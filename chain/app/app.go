package app

import (
	clienthelpers "cosmossdk.io/client/v2/helpers"
	"cosmossdk.io/core/appmodule"
	"cosmossdk.io/depinject"
	"cosmossdk.io/log/v2"
	storetypes "github.com/cosmos/cosmos-sdk/store/v2/types"
	upgradekeeper "github.com/cosmos/cosmos-sdk/x/upgrade/keeper"

	abci "github.com/cometbft/cometbft/abci/types"
	cmtproto "github.com/cometbft/cometbft/proto/tendermint/types"
	dbm "github.com/cosmos/cosmos-db"
	"github.com/cosmos/cosmos-sdk/baseapp"
	"github.com/cosmos/cosmos-sdk/baseapp/txnrunner"
	"github.com/cosmos/cosmos-sdk/client"
	"github.com/cosmos/cosmos-sdk/codec"
	codectypes "github.com/cosmos/cosmos-sdk/codec/types"
	"github.com/cosmos/cosmos-sdk/runtime"
	"github.com/cosmos/cosmos-sdk/server"
	"github.com/cosmos/cosmos-sdk/server/api"
	"github.com/cosmos/cosmos-sdk/server/config"
	servertypes "github.com/cosmos/cosmos-sdk/server/types"
	sdk "github.com/cosmos/cosmos-sdk/types"
	"github.com/cosmos/cosmos-sdk/types/mempool"
	"github.com/cosmos/cosmos-sdk/types/module"
	"github.com/cosmos/cosmos-sdk/x/auth"
	authkeeper "github.com/cosmos/cosmos-sdk/x/auth/keeper"
	authsims "github.com/cosmos/cosmos-sdk/x/auth/simulation"
	authtypes "github.com/cosmos/cosmos-sdk/x/auth/types"
	authzkeeper "github.com/cosmos/cosmos-sdk/x/authz/keeper"
	bankkeeper "github.com/cosmos/cosmos-sdk/x/bank/keeper"
	consensuskeeper "github.com/cosmos/cosmos-sdk/x/consensus/keeper"
	distrkeeper "github.com/cosmos/cosmos-sdk/x/distribution/keeper"
	feegrantkeeper "github.com/cosmos/cosmos-sdk/x/feegrant/keeper"
	"github.com/cosmos/cosmos-sdk/x/genutil"
	genutiltypes "github.com/cosmos/cosmos-sdk/x/genutil/types"
	govkeeper "github.com/cosmos/cosmos-sdk/x/gov/keeper"
	govtypes "github.com/cosmos/cosmos-sdk/x/gov/types"
	mintkeeper "github.com/cosmos/cosmos-sdk/x/mint/keeper"
	paramskeeper "github.com/cosmos/cosmos-sdk/x/params/keeper"
	slashingkeeper "github.com/cosmos/cosmos-sdk/x/slashing/keeper"
	stakingkeeper "github.com/cosmos/cosmos-sdk/x/staking/keeper"
	txsigning "github.com/cosmos/cosmos-sdk/x/tx/signing"
	icacontrollerkeeper "github.com/cosmos/ibc-go/v11/modules/apps/27-interchain-accounts/controller/keeper"
	icahostkeeper "github.com/cosmos/ibc-go/v11/modules/apps/27-interchain-accounts/host/keeper"
	ibctransferkeeper "github.com/cosmos/ibc-go/v11/modules/apps/transfer/keeper"
	ibckeeper "github.com/cosmos/ibc-go/v11/modules/core/keeper"
	"github.com/ethereum/go-ethereum/common"

	// Cosmos EVM v0.7.4 (Ethermint successor) — wired manually because it
	// ships no depinject module config; see wireEVM below.
	evmante "github.com/cosmos/evm/ante"
	antetypes "github.com/cosmos/evm/ante/types"
	evmcrypto "github.com/cosmos/evm/crypto/codec"
	evmmempool "github.com/cosmos/evm/mempool"
	cosmosevmserver "github.com/cosmos/evm/server"
	feemarket "github.com/cosmos/evm/x/feemarket"
	feemarketkeeper "github.com/cosmos/evm/x/feemarket/keeper"
	feemarkettypes "github.com/cosmos/evm/x/feemarket/types"
	evm "github.com/cosmos/evm/x/vm"
	evmkeeper "github.com/cosmos/evm/x/vm/keeper"
	vmrunner "github.com/cosmos/evm/x/vm/runner"
	evmtypes "github.com/cosmos/evm/x/vm/types"

	"blackchain/docs"
	blackchainmodulekeeper "blackchain/x/blackchain/keeper"
)

const (
	// Name is the name of the application.
	Name = "blackchain"
	// AccountAddressPrefix is the prefix for accounts addresses.
	AccountAddressPrefix = "black"
	// ChainCoinType is the coin type of the chain.
	ChainCoinType = 118
)

// DefaultNodeHome default home directories for the application daemon
var DefaultNodeHome string

var (
	_ runtime.AppI            = (*App)(nil)
	_ servertypes.Application = (*App)(nil)
)

// App extends an ABCI application, but with most of its parameters exported.
// They are exported for convenience in creating helper functions, as object
// capabilities aren't needed for testing.
type App struct {
	*runtime.App
	legacyAmino       *codec.LegacyAmino
	appCodec          codec.Codec
	txConfig          client.TxConfig
	interfaceRegistry codectypes.InterfaceRegistry

	// keepers
	// only keepers required by the app are exposed
	// the list of all modules is available in the app_config
	AuthKeeper            authkeeper.AccountKeeper
	BankKeeper            bankkeeper.Keeper
	StakingKeeper         *stakingkeeper.Keeper
	SlashingKeeper        slashingkeeper.Keeper
	MintKeeper            mintkeeper.Keeper
	DistrKeeper           distrkeeper.Keeper
	GovKeeper             *govkeeper.Keeper
	UpgradeKeeper         *upgradekeeper.Keeper
	AuthzKeeper           authzkeeper.Keeper
	FeegrantKeeper        feegrantkeeper.Keeper
	ConsensusParamsKeeper consensuskeeper.Keeper
	ParamsKeeper          paramskeeper.Keeper // SDK 0.54: legacy subspace provider for auth module

	// Cosmos EVM keepers (manual wiring, see wireEVMStoresAndKeepers)
	FeeMarketKeeper feemarketkeeper.Keeper
	EVMKeeper       *evmkeeper.Keeper
	// EVMMempool is the Krakatoa app-side EVM mempool (Cosmos EVM v0.7
	// migration guide 5a). It is required by the eth JSON-RPC server:
	// backend.Mempool needs GetTxPool, which only this mempool provides.
	EVMMempool *evmmempool.Mempool
	// evmModule is the x/vm AppModule instance (needed for HydrateGlobals).
	evmModule evm.AppModule

	// pendingTxListener is notified of pending EVM tx hashes (JSON-RPC streaming).
	pendingTxListener func(common.Hash)

	// ibc keepers
	IBCKeeper           *ibckeeper.Keeper
	ICAControllerKeeper *icacontrollerkeeper.Keeper
	ICAHostKeeper       *icahostkeeper.Keeper
	TransferKeeper      *ibctransferkeeper.Keeper

	// simulation manager
	sm               *module.SimulationManager
	BlackchainKeeper blackchainmodulekeeper.Keeper
}

func init() {
	var err error
	clienthelpers.EnvPrefix = Name
	DefaultNodeHome, err = clienthelpers.GetNodeHomeDirectory("." + Name)
	if err != nil {
		panic(err)
	}
}

// ProvideEVMCustomGetSigner supplies the custom GetSigners function for
// MsgEthereumTx to depinject (many-per-container type). Exported because
// depinject.Provide requires an exported provider function.
func ProvideEVMCustomGetSigner() txsigning.CustomGetSigner {
	return evmtypes.MsgEthereumTxCustomGetSigner
}

// AppConfig returns the default app config.
func AppConfig() depinject.Config {
	return depinject.Configs(
		appConfig,
		// MsgEthereumTx has no static cosmos.msg.v1.signer field; its
		// signers come from the eth tx itself. Provide the custom getter
		// (many-per-container type: Provide, not Supply) or
		// ProvideInterfaceRegistry panics at startup.
		depinject.Provide(ProvideEVMCustomGetSigner),
		depinject.Supply(
			// supply custom module basics
			map[string]module.AppModuleBasic{
				genutiltypes.ModuleName: genutil.NewAppModuleBasic(genutiltypes.DefaultMessageValidator),
				// Cosmos EVM modules have no depinject config; their basics are
				// supplied here so interfaces + default genesis register early.
				evmtypes.ModuleName:       evm.AppModuleBasic{},
				feemarkettypes.ModuleName: feemarket.AppModuleBasic{},
			},
		),
	)
}

// New returns a reference to an initialized App.
func New(
	logger log.Logger,
	db dbm.DB,
	loadLatest bool,
	appOpts servertypes.AppOptions,
	baseAppOptions ...func(*baseapp.BaseApp),
) *App {
	var (
		app        = &App{}
		appBuilder *runtime.AppBuilder

		// merge the AppConfig and other configuration in one config
		appConfig = depinject.Configs(
			AppConfig(),
			depinject.Supply(
				appOpts, // supply app options
				logger,  // supply logger

				// Supply with IBC keeper getter for the IBC modules with App Wiring.
				// The IBC Keeper cannot be passed because it has not been initiated yet.
				// Passing the getter, the app IBC Keeper will always be accessible.
				// This needs to be removed after IBC supports App Wiring.
				app.GetIBCKeeper,

				// here alternative options can be supplied to the DI container.
				// those options can be used f.e to override the default behavior of some modules.
				// for instance supplying a custom address codec for not using bech32 addresses.
				// read the depinject documentation and depinject module wiring for more information
				// on available options and how to use them.
			),
		)
	)

	var appModules map[string]appmodule.AppModule
	if err := depinject.Inject(appConfig,
		&appBuilder,
		&appModules,
		&app.appCodec,
		&app.legacyAmino,
		&app.txConfig,
		&app.interfaceRegistry,
		&app.AuthKeeper,
		&app.BankKeeper,
		&app.StakingKeeper,
		&app.SlashingKeeper,
		&app.MintKeeper,
		&app.DistrKeeper,
		&app.GovKeeper,
		&app.UpgradeKeeper,
		&app.AuthzKeeper,
		&app.FeegrantKeeper,
		&app.ParamsKeeper,
		&app.ConsensusParamsKeeper,
		&app.BlackchainKeeper,
	); err != nil {
		panic(err)
	}

	// add to default baseapp options
	// enable optimistic execution
	baseAppOptions = append(baseAppOptions, baseapp.SetOptimisticExecution())

	// build app
	app.App = appBuilder.Build(db, baseAppOptions...)

	// EVM stores + keepers (must run BEFORE app.Load below, which loads stores).
	app.wireEVMStoresAndKeepers(appOpts, logger)

	// register legacy modules
	if err := app.registerIBCModules(appOpts); err != nil {
		panic(err)
	}

	/****  Module Options ****/

	// create the simulation manager and define the order of the modules for deterministic simulations
	// NOTE (SDK 0.54): the "auth" legacy subspace is already created by
	// depinject during Inject; calling Subspace() again panics ("already
	// occupied"), so reuse it via GetSubspace with a fallback.
	authSubspace, ok := app.ParamsKeeper.GetSubspace(authtypes.ModuleName)
	if !ok {
		authSubspace = app.ParamsKeeper.Subspace(authtypes.ModuleName)
	}
	overrideModules := map[string]module.AppModuleSimulation{
		authtypes.ModuleName: auth.NewAppModule(app.appCodec, app.AuthKeeper, authsims.RandomGenesisAccounts, authSubspace),
	}
	app.sm = module.NewSimulationManagerFromAppModules(app.ModuleManager.Modules, overrideModules)

	app.sm.RegisterStoreDecoders()

	// A custom InitChainer sets if extra pre-init-genesis logic is required.
	// This is necessary for manually registered modules that do not support app wiring.
	// Manually set the module version map as shown below.
	// The upgrade module will automatically handle de-duplication of the module version map.
	app.SetInitChainer(func(ctx sdk.Context, req *abci.RequestInitChain) (*abci.ResponseInitChain, error) {
		if err := app.UpgradeKeeper.SetModuleVersionMap(ctx, app.ModuleManager.GetVersionMap()); err != nil {
			return nil, err
		}
		return app.App.InitChainer(ctx, req)
	})

	if err := app.Load(loadLatest); err != nil {
		panic(err)
	}

	// EVM modules, orders, ante handler, tx runner (must run AFTER Load,
	// because runtime.App.Load re-applies the depinject order lists).
	app.wireEVMModules()

	if loadLatest {
		// Hydrate EVM globals from KV so evmCoinInfo is populated before any
		// RPC handler runs (Cosmos EVM v0.7 migration guide, #1126).
		ctx := app.NewContextLegacy(true, cmtproto.Header{
			Height:  app.LastBlockHeight(),
			ChainID: app.ChainID(),
		})
		app.evmModule.HydrateGlobals(ctx)
	}

	return app
}

// LegacyAmino returns App's amino codec.
func (app *App) LegacyAmino() *codec.LegacyAmino {
	return app.legacyAmino
}

// AppCodec returns App's app codec.
func (app *App) AppCodec() codec.Codec {
	return app.appCodec
}

// InterfaceRegistry returns App's InterfaceRegistry.
func (app *App) InterfaceRegistry() codectypes.InterfaceRegistry {
	return app.interfaceRegistry
}

// TxConfig returns App's TxConfig
func (app *App) TxConfig() client.TxConfig {
	return app.txConfig
}

// GetKey returns the KVStoreKey for the provided store key.
func (app *App) GetKey(storeKey string) *storetypes.KVStoreKey {
	kvStoreKey, ok := app.UnsafeFindStoreKey(storeKey).(*storetypes.KVStoreKey)
	if !ok {
		return nil
	}
	return kvStoreKey
}

// SimulationManager implements the SimulationApp interface
func (app *App) SimulationManager() *module.SimulationManager {
	return app.sm
}

// RegisterAPIRoutes registers all application module routes with the provided
// API server.
func (app *App) RegisterAPIRoutes(apiSvr *api.Server, apiConfig config.APIConfig) {
	app.App.RegisterAPIRoutes(apiSvr, apiConfig)
	// register swagger API in app.go so that other applications can override easily
	if err := server.RegisterSwaggerAPI(apiSvr.ClientCtx, apiSvr.Router, apiConfig.Swagger); err != nil {
		panic(err)
	}

	// register app's OpenAPI routes.
	docs.RegisterOpenAPIService(Name, apiSvr.Router)
}

// GetMaccPerms returns a copy of the module account permissions
//
// NOTE: This is solely to be used for testing purposes.
func GetMaccPerms() map[string][]string {
	dup := make(map[string][]string)
	for _, perms := range moduleAccPerms {
		dup[perms.GetAccount()] = perms.GetPermissions()
	}

	return dup
}

// BlockedAddresses returns all the app's blocked account addresses.
func BlockedAddresses() map[string]bool {
	result := make(map[string]bool)

	if len(blockAccAddrs) > 0 {
		for _, addr := range blockAccAddrs {
			result[addr] = true
		}
	} else {
		for addr := range GetMaccPerms() {
			result[addr] = true
		}
	}

	return result
}

// ---------------------------------------------------------------------------
// Cosmos EVM wiring (Jalur A, 20 Nov 2026)
//
// Cosmos EVM v0.7.4 ships no depinject module config, so x/vm + x/feemarket
// are wired manually into this Ignite (depinject) app, following the
// v0.6.x -> v0.7.0 migration guide in the Cosmos EVM repo.
// Split in two on purpose:
//   - wireEVMStoresAndKeepers runs BEFORE app.Load (stores must be mounted
//     before LoadLatestVersion).
//   - wireEVMModules runs AFTER app.Load, because runtime.App.Load
//     re-applies the depinject order lists (which don't know evm/feemarket)
//     and would panic on the "forgotten modules" assertion otherwise.
// ---------------------------------------------------------------------------

// evmChainID is the EVM chain ID for BLACKCHAIN (BKC identity, decided
// 2026-11-20, Session 4): 20261120 (0x1352C10). Verified NOT REGISTERED in
// the ethereum-lists/chains registry (2,894 chains, checked 2026-11-20);
// it does not collide with Evmos 9000/9001, Geth devnet 1337, or the old
// Cosmos EVM default 262144 (which is registered as "MPCQ Mainnet").
// The CometBFT chain-id is "blackchain_20261120-1" (Evmos-style:
// <name>_<evmChainID>-<revision>). The EVM denom is "abkc" (atto BKC,
// 18 decimals, display BKC) — see app/config.go DefaultBondDenom.
var evmChainID = uint64(20261120)

func (app *App) wireEVMStoresAndKeepers(appOpts servertypes.AppOptions, logger log.Logger) {
	evmStoreKey := storetypes.NewKVStoreKey(evmtypes.StoreKey)
	feemarketStoreKey := storetypes.NewKVStoreKey(feemarkettypes.StoreKey)
	evmObjectKey := storetypes.NewObjectStoreKey(evmtypes.ObjectKey)

	// RegisterStores appends to the app's store keys AND mounts them
	// (MountStores handles ObjectStoreKey via its type switch).
	if err := app.RegisterStores(evmStoreKey, feemarketStoreKey, evmObjectKey); err != nil {
		panic(err)
	}

	// Keys the EVM keeper may touch cross-module (StateDB access).
	nonTransientKeys := append(append([]storetypes.StoreKey{}, app.GetStoreKeys()...), evmStoreKey, feemarketStoreKey, evmObjectKey)

	app.FeeMarketKeeper = feemarketkeeper.NewKeeper(
		app.appCodec,
		authtypes.NewModuleAddress(govtypes.ModuleName),
		feemarketStoreKey,
	)

	app.EVMKeeper = evmkeeper.NewKeeper(
		app.appCodec,
		evmStoreKey, evmObjectKey, nonTransientKeys,
		authtypes.NewModuleAddress(govtypes.ModuleName),
		app.AuthKeeper,
		app.BankKeeper,
		app.StakingKeeper,
		app.FeeMarketKeeper,
		&app.ConsensusParamsKeeper,
		nil, // no ERC20 keeper in v0.1: erc20 precompile disabled (nil is handled explicitly in the keeper)
		evmChainID,
		"", // no tracer
	)

	// EVM ante handler + tx runner must be set BEFORE app.Load below:
	// BaseApp is sealed by LoadLatestVersion and SetAnteHandler panics after.
	app.SetAnteHandler(evmante.NewAnteHandler(evmante.HandlerOptions{
		Cdc:                    app.appCodec,
		AccountKeeper:          app.AuthKeeper,
		BankKeeper:             app.BankKeeper,
		ExtensionOptionChecker: antetypes.HasDynamicFeeExtensionOption,
		EvmKeeper:              app.EVMKeeper,
		FeegrantKeeper:         app.FeegrantKeeper,
		IBCKeeper:              app.IBCKeeper,
		FeeMarketKeeper:        app.FeeMarketKeeper,
		SignModeHandler:        app.txConfig.SignModeHandler(),
		SigGasConsumer:         evmante.SigVerificationGasConsumer,
		MaxTxGasWanted:         1_000_000_000,
		DynamicFeeChecker:      true,
		PendingTxListener: func(h common.Hash) {
			if app.pendingTxListener != nil {
				app.pendingTxListener(h)
			}
		},
	}))

	// EVM tx runner: fixes log.Index / transactionIndex on receipts (#1132).
	vmrunner.SetRunner(app.BaseApp, txnrunner.NewDefaultRunner(app.txConfig.TxDecoder()))

	// Krakatoa app-side EVM mempool (see configureEVMMempool). Must run
	// after SetAnteHandler and before app.Load (all setters below panic
	// on a sealed BaseApp).
	app.configureEVMMempool(appOpts, logger)
}

// configureEVMMempool wires the Krakatoa app-side EVM mempool (Cosmos EVM
// v0.7 migration guide 5a, reference: evmd/mempool.go). This is NOT
// optional if the eth JSON-RPC server is used: its backend requires
// backend.Mempool (GetTxPool), which only this mempool implements — with
// the stock CometBFT mempool, StartJSONRPC fails with
// "json-rpc server requires backend.Mempool".
//
// Requires config.toml mempool.type = "app" (CometBFT v0.39). Opt-out:
// set mempool.max-txs=-1 (app.toml [mempool] / --mempool.max-txs flag) —
// GetCosmosPoolMaxTx then returns a negative value and we skip, falling
// back to the stock mempool (and JSON-RPC will refuse to start).
func (app *App) configureEVMMempool(appOpts servertypes.AppOptions, logger log.Logger) {
	cosmosPoolMaxTx := cosmosevmserver.GetCosmosPoolMaxTx(appOpts, logger)
	if cosmosPoolMaxTx < 0 {
		logger.Info("EVM mempool disabled (mempool.max-txs < 0); eth JSON-RPC requires it and will fail to start")
		return
	}

	mpConfig := cosmosevmserver.ResolveMempoolConfig(app.AnteHandler(), appOpts, logger)
	txEncoder := evmmempool.NewTxEncoder(app.txConfig)
	// Two DISTINCT rechecker instances (guide warning): they feed different
	// subpools (EVM eth-tx pool vs Cosmos pool) and need independent state.
	evmRechecker := evmmempool.NewTxRechecker(mpConfig.AnteHandler, txEncoder)
	cosmosRechecker := evmmempool.NewTxRechecker(mpConfig.AnteHandler, txEncoder)
	checkTxTimeout := cosmosevmserver.GetMempoolCheckTxTimeout(appOpts, logger)

	mempool := evmmempool.NewMempool(
		app.CreateQueryContext, logger,
		app.EVMKeeper, app.FeeMarketKeeper, app.txConfig,
		evmRechecker, cosmosRechecker, mpConfig, cosmosPoolMaxTx,
	)
	app.EVMMempool = mempool
	app.SetPrepareProposal(baseapp.NewDefaultProposalHandler(mempool, NewNoCheckProposalTxVerifier(app.BaseApp)).PrepareProposalHandler())
	app.SetInsertTxHandler(mempool.NewInsertTxHandler(app.TxDecode))
	app.SetReapTxsHandler(mempool.NewReapTxsHandler())
	app.SetCheckTxHandler(mempool.NewCheckTxHandler(app.TxDecode, checkTxTimeout))
	app.SetMempool(mempool)
}

// noCheckProposalTxVerifier implements baseapp.ProposalTxVerifier by
// skipping ante-handler re-verification of proposal txs. This is the
// evmd reference pattern: with the Krakatoa mempool every tx in a proposal
// was already validated at CheckTx, so the check is redundant.
type noCheckProposalTxVerifier struct {
	bApp *baseapp.BaseApp
}

// NewNoCheckProposalTxVerifier returns a ProposalTxVerifier that only
// encodes/decodes txs without re-running verification.
func NewNoCheckProposalTxVerifier(bApp *baseapp.BaseApp) baseapp.ProposalTxVerifier {
	return noCheckProposalTxVerifier{bApp: bApp}
}

func (v noCheckProposalTxVerifier) PrepareProposalVerifyTx(tx sdk.Tx) ([]byte, error) {
	return v.bApp.TxEncode(tx)
}

func (v noCheckProposalTxVerifier) ProcessProposalVerifyTx(txBz []byte) (sdk.Tx, error) {
	return v.bApp.TxDecode(txBz)
}

func (v noCheckProposalTxVerifier) TxDecode(txBz []byte) (sdk.Tx, error) {
	return v.bApp.TxDecode(txBz)
}

func (v noCheckProposalTxVerifier) TxEncode(tx sdk.Tx) ([]byte, error) {
	return v.bApp.TxEncode(tx)
}

func (app *App) wireEVMModules() {
	vmModule := evm.NewAppModule(app.EVMKeeper, app.AuthKeeper, app.BankKeeper, app.AuthKeeper.AddressCodec())
	feemarketModule := feemarket.NewAppModule(app.FeeMarketKeeper)
	app.evmModule = vmModule

	app.ModuleManager.Modules[evmtypes.ModuleName] = vmModule
	app.ModuleManager.Modules[feemarkettypes.ModuleName] = feemarketModule

	// Extend every order list with the new modules (full lists, or the
	// Manager's "forgotten modules" assertion panics).
	appendOrder := func(list []string, names ...string) []string {
		out := append([]string{}, list...)
		return append(out, names...)
	}
	if len(app.ModuleManager.OrderPreBlockers) > 0 {
		app.ModuleManager.SetOrderPreBlockers(appendOrder(app.ModuleManager.OrderPreBlockers, evmtypes.ModuleName)...)
	}
	if len(app.ModuleManager.OrderBeginBlockers) > 0 {
		app.ModuleManager.SetOrderBeginBlockers(appendOrder(app.ModuleManager.OrderBeginBlockers, feemarkettypes.ModuleName, evmtypes.ModuleName)...)
	}
	if len(app.ModuleManager.OrderEndBlockers) > 0 {
		app.ModuleManager.SetOrderEndBlockers(appendOrder(app.ModuleManager.OrderEndBlockers, feemarkettypes.ModuleName, evmtypes.ModuleName)...)
	}
	if len(app.ModuleManager.OrderInitGenesis) > 0 {
		// NOTE (InitGenesis order): x/vm InitGenesis sets the global
		// evmCoinInfo (SetGlobalConfigVariables); the EVM ante handler
		// needs it when genutil delivers the genesis txs. The depinject
		// order lists genutil BEFORE the appended evm, so insert
		// feemarket/evm BEFORE genutil in InitGenesis.
		initOrder := app.ModuleManager.OrderInitGenesis
		initOrderEVM := make([]string, 0, len(initOrder)+2)
		inserted := false
		for _, name := range initOrder {
			if name == genutiltypes.ModuleName && !inserted {
				initOrderEVM = append(initOrderEVM, feemarkettypes.ModuleName, evmtypes.ModuleName)
				inserted = true
			}
			initOrderEVM = append(initOrderEVM, name)
		}
		if !inserted {
			initOrderEVM = append(initOrderEVM, feemarkettypes.ModuleName, evmtypes.ModuleName)
		}
		app.ModuleManager.SetOrderInitGenesis(initOrderEVM...)
	}
	if len(app.ModuleManager.OrderExportGenesis) > 0 {
		app.ModuleManager.SetOrderExportGenesis(appendOrder(app.ModuleManager.OrderExportGenesis, feemarkettypes.ModuleName, evmtypes.ModuleName)...)
	}
	if len(app.ModuleManager.OrderMigrations) > 0 {
		app.ModuleManager.SetOrderMigrations(appendOrder(app.ModuleManager.OrderMigrations, feemarkettypes.ModuleName, evmtypes.ModuleName)...)
	}
	if len(app.ModuleManager.OrderPrepareCheckStaters) > 0 {
		app.ModuleManager.SetOrderPrepareCheckStaters(appendOrder(app.ModuleManager.OrderPrepareCheckStaters, feemarkettypes.ModuleName, evmtypes.ModuleName)...)
	}
	if len(app.ModuleManager.OrderPrecommiters) > 0 {
		app.ModuleManager.SetOrderPrecommiters(appendOrder(app.ModuleManager.OrderPrecommiters, feemarkettypes.ModuleName, evmtypes.ModuleName)...)
	}

	// Register msg + query servers for the new modules.
	// NOTE: the app's interface registry never saw the EVM types, because
	// SetupAppBuilder only calls RegisterInterfaces for depinject modules.
	// Register them explicitly first, or MsgServiceRouter panics
	// ("type_url ... MsgEthereumTx has not been registered yet").
	evm.AppModuleBasic{}.RegisterInterfaces(app.interfaceRegistry)
	feemarket.AppModuleBasic{}.RegisterInterfaces(app.interfaceRegistry)
	evm.AppModuleBasic{}.RegisterLegacyAminoCodec(app.legacyAmino)
	feemarket.AppModuleBasic{}.RegisterLegacyAminoCodec(app.legacyAmino)
	// Cosmos EVM crypto types (ethsecp256k1 pubkey/privkey) for auth
	// accounts whose address is the eth address.
	evmcrypto.RegisterInterfaces(app.interfaceRegistry)
	cfg := module.NewConfigurator(app.appCodec, app.MsgServiceRouter(), app.GRPCQueryRouter())
	vmModule.RegisterServices(cfg)
	feemarketModule.RegisterServices(cfg)
}

// GetMempool returns the app mempool as an ExtMempool (required by the
// Cosmos EVM JSON-RPC server's Application interface).
func (app *App) GetMempool() mempool.ExtMempool {
	if mp, ok := app.Mempool().(mempool.ExtMempool); ok {
		return mp
	}
	return nil
}

// RegisterPendingTxListener stores the listener the JSON-RPC server uses to
// stream pending EVM transactions.
func (app *App) RegisterPendingTxListener(listener func(common.Hash)) {
	app.pendingTxListener = listener
}

// GetEVMKeeper exposes the EVM keeper (used by tests / tooling).
func (app *App) GetEVMKeeper() *evmkeeper.Keeper { return app.EVMKeeper }

// GetFeeMarketKeeper exposes the fee-market keeper.
func (app *App) GetFeeMarketKeeper() feemarketkeeper.Keeper { return app.FeeMarketKeeper }
