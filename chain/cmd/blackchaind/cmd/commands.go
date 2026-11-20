package cmd

import (
	"errors"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"cosmossdk.io/log/v2"
	confixcmd "cosmossdk.io/tools/confix/cmd"
	tcmd "github.com/cometbft/cometbft/cmd/cometbft/commands"
	dbm "github.com/cosmos/cosmos-db"
	"github.com/cosmos/cosmos-sdk/client"
	"github.com/cosmos/cosmos-sdk/client/debug"
	"github.com/cosmos/cosmos-sdk/client/flags"
	"github.com/cosmos/cosmos-sdk/client/keys"
	"github.com/cosmos/cosmos-sdk/client/pruning"
	"github.com/cosmos/cosmos-sdk/client/rpc"
	"github.com/cosmos/cosmos-sdk/client/snapshot"
	"github.com/cosmos/cosmos-sdk/server"
	servertypes "github.com/cosmos/cosmos-sdk/server/types"
	"github.com/cosmos/cosmos-sdk/types/module"
	"github.com/cosmos/cosmos-sdk/version"
	authcmd "github.com/cosmos/cosmos-sdk/x/auth/client/cli"
	banktypes "github.com/cosmos/cosmos-sdk/x/bank/types"
	genutilcli "github.com/cosmos/cosmos-sdk/x/genutil/client/cli"
	cosmosevmserver "github.com/cosmos/evm/server"

	"blackchain/app"
)

// blackchainStartCmd returns the Cosmos EVM start command with the
// project's EVM chain ID as the default for --evm.evm-chain-id.
// Upstream default is 262144 (Cosmos EVM DefaultEVMChainID), which the
// JSON-RPC backend uses to validate incoming eth txs (SendRawTransaction
// rejects txs whose chain ID differs). The keeper-side chain ID alone
// (app.evmChainID) is NOT enough: eth_chainId would report the new ID
// while SendRawTransaction still expected 262144 (F23, 2026-11-20).
// Setting the flag's Value (without marking it Changed) keeps the flag
// overridable on the command line and keeps app.toml [evm] evm-chain-id
// effective when present.
func blackchainStartCmd() *cobra.Command {
	cmd := cosmosevmserver.StartCmd(cosmosevmserver.NewDefaultStartOptions(newEVMApp, app.DefaultNodeHome))
	if f := cmd.Flags().Lookup("evm.evm-chain-id"); f != nil {
		f.DefValue = "20261120"
		_ = f.Value.Set("20261120")
	}
	return cmd
}

func initRootCmd(
	rootCmd *cobra.Command,
	txConfig client.TxConfig,
	basicManager module.BasicManager,
) {
	rootCmd.AddCommand(
		genutilcli.InitCmd(basicManager, app.DefaultNodeHome),
		NewInPlaceTestnetCmd(),
		NewTestnetMultiNodeCmd(basicManager, banktypes.GenesisBalancesIterator{}),
		debug.Cmd(),
		confixcmd.ConfigCommand(),
		pruning.Cmd(newApp, app.DefaultNodeHome),
		snapshot.Cmd(newApp),
	)

	// Cosmos EVM start command: serves the eth JSON-RPC (eth_blockNumber,
	// eth_chainId, ...) alongside CometBFT. It replaces the stock SDK start
	// command, which has no JSON-RPC. The other commands that
	// AddCommandsWithStartCmdOptions used to add are replicated below so
	// `comet`, `export`, `version` and `rollback` keep working.
	cometCmd := &cobra.Command{
		Use:     "comet",
		Aliases: []string{"cometbft", "tendermint"},
		Short:   "CometBFT subcommands",
	}
	cometCmd.AddCommand(
		server.ShowNodeIDCmd(),
		server.ShowValidatorCmd(),
		server.ShowAddressCmd(),
		server.VersionCmd(),
		tcmd.ResetAllCmd,
		tcmd.ResetStateCmd,
		server.BootstrapStateCmd(newApp),
	)
	rootCmd.AddCommand(
		blackchainStartCmd(),
		cometCmd,
		server.ExportCmd(appExport, app.DefaultNodeHome),
		version.NewVersionCommand(),
		server.NewRollbackCmd(newApp, app.DefaultNodeHome),
	)

	// add keybase, auxiliary RPC, query, genesis, and tx child commands
	rootCmd.AddCommand(
		server.StatusCommand(),
		genutilcli.Commands(txConfig, basicManager, app.DefaultNodeHome),
		queryCommand(),
		txCommand(),
		keys.Commands(),
	)
}

func queryCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:                        "query",
		Aliases:                    []string{"q"},
		Short:                      "Querying subcommands",
		DisableFlagParsing:         false,
		SuggestionsMinimumDistance: 2,
		RunE:                       client.ValidateCmd,
	}

	cmd.AddCommand(
		rpc.WaitTxCmd(),
		rpc.ValidatorCommand(),
		server.QueryBlockCmd(),
		authcmd.QueryTxsByEventsCmd(),
		server.QueryBlocksCmd(),
		authcmd.QueryTxCmd(),
		server.QueryBlockResultsCmd(),
	)

	return cmd
}

func txCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:                        "tx",
		Short:                      "Transactions subcommands",
		DisableFlagParsing:         false,
		SuggestionsMinimumDistance: 2,
		RunE:                       client.ValidateCmd,
	}

	cmd.AddCommand(
		authcmd.GetSignCommand(),
		authcmd.GetSignBatchCommand(),
		authcmd.GetMultiSignCommand(),
		authcmd.GetMultiSignBatchCmd(),
		authcmd.GetValidateSignaturesCommand(),
		flags.LineBreak,
		authcmd.GetBroadcastCommand(),
		authcmd.GetEncodeCommand(),
		authcmd.GetDecodeCommand(),
		authcmd.GetSimulateCmd(),
	)

	return cmd
}

// newApp creates the application
func newApp(
	logger log.Logger,
	db dbm.DB,
	appOpts servertypes.AppOptions,
) servertypes.Application {
	baseappOptions := server.DefaultBaseappOptions(appOpts)

	return app.New(
		logger, db, true,
		appOpts,
		baseappOptions...,
	)
}

// newEVMApp creates the application for the Cosmos EVM start command.
// The returned app must satisfy cosmosevmserver.Application: the SDK
// Application interface + AppWithPendingTxStream + GetMempool() ExtMempool
// (all implemented in app.App).
func newEVMApp(
	logger log.Logger,
	db dbm.DB,
	appOpts servertypes.AppOptions,
) cosmosevmserver.Application {
	baseappOptions := server.DefaultBaseappOptions(appOpts)

	return app.New(
		logger, db, true,
		appOpts,
		baseappOptions...,
	)
}

// appExport creates a new app (optionally at a given height) and exports state.
func appExport(
	logger log.Logger,
	db dbm.DB,
	height int64,
	forZeroHeight bool,
	jailAllowedAddrs []string,
	appOpts servertypes.AppOptions,
	modulesToExport []string,
) (servertypes.ExportedApp, error) {
	var bApp *app.App

	// this check is necessary as we use the flag in x/upgrade.
	// we can exit more gracefully by checking the flag here.
	homePath, ok := appOpts.Get(flags.FlagHome).(string)
	if !ok || homePath == "" {
		return servertypes.ExportedApp{}, errors.New("application home not set")
	}

	viperAppOpts, ok := appOpts.(*viper.Viper)
	if !ok {
		return servertypes.ExportedApp{}, errors.New("appOpts is not viper.Viper")
	}

	appOpts = viperAppOpts
	if height != -1 {
		bApp = app.New(logger, db, false, appOpts)
		if err := bApp.LoadHeight(height); err != nil {
			return servertypes.ExportedApp{}, err
		}
	} else {
		bApp = app.New(logger, db, true, appOpts)
	}

	return bApp.ExportAppStateAndValidators(forZeroHeight, jailAllowedAddrs, modulesToExport)
}
