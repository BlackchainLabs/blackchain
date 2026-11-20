package backend

// BLACKCHAIN Fase 1 — batch admission (Sesi 9, 2026-11-20).
//
// eth_sendRawTransactionBatch: satu panggilan JSON-RPC berisi maks 100 raw
// tx. Desain: docs/16-phase1-ingest-design.md §2–§3.
//
// Arsitektur admission (bukan eksekusi — eksekusi tetap serial di Fase 1):
//   - Fase A (paralel): decode RLP + recover pengirim (secp256k1, bagian
//     termahal) + ValidateBasic + BuildTx, dijalankan worker pool 2×vCPU.
//   - Fase B (sharded submit): tx dikelompokkan per pengirim, diurutkan
//     berdasarkan nonce, lalu tiap pengirim diserahkan ke salah satu dari
//     16 shard (berdasarkan hash alamat pengirim). Shard berjalan paralel;
//     di dalam satu shard, tx dari pengirim yang sama diserahkan berurutan
//     (FIFO nonce). Bila satu tx gagal, tx berikutnya dari pengirim yang
//     sama di batch itu TIDAK dibuang diam-diam: hasilnya error eksplisit
//     "held: preceding transaction ... failed" supaya client bisa retry.
//   - Proteksi DoS (docs/16 §2.4): batas 100 tx/batch, 10 MB/batch, maks
//     4 batch bersamaan, 20 tx/detik per pengirim, maks 100 tx tertunda per
//     pengirim, dedup hash (cache 100.000 hash terakhir). Floor harga gas
//     jaringan (base fee) TETAP ditegakkan oleh mempool insert seperti pada
//     jalur tunggal; di sini hanya ada pre-check murah (fee cap tidak
//     negatif) sebelum recover yang mahal.
//
// Yang SENGAJA tidak diubah di sesi ini: lock internal mempool Krakatoa
// (go-ethereum-style TxPool + satu insert queue FIFO) — rewrite 16-shard
// atas txpool itu adalah pekerjaan Fase 1b tersendiri (lihat
// docs/19-phase1-implementation.md). Sharding di sini berlaku di lapisan
// admission (urutan masuk), bukan di dalam txpool.

import (
	"context"
	"fmt"
	"hash/fnv"
	"runtime"
	"sort"
	"sync"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/common/hexutil"
	ethtypes "github.com/ethereum/go-ethereum/core/types"
	"github.com/pkg/errors"
	"go.opentelemetry.io/otel/attribute"

	evmtrace "github.com/cosmos/evm/trace"
	evmtypes "github.com/cosmos/evm/x/vm/types"

	sdk "github.com/cosmos/cosmos-sdk/types"
)

// Batas batch admission (docs/16 §2.2–§2.4, §3).
const (
	// MaxBatchTxs is the maximum number of raw transactions per batch call.
	MaxBatchTxs = 100
	// MaxBatchBytes is the maximum total size of a batch call.
	MaxBatchBytes = 10 << 20 // 10 MB
	// BatchNumShards is the number of admission shards, keyed by sender hash.
	BatchNumShards = 16
	// BatchMaxPendingPerSender is the max number of in-flight txs per sender.
	BatchMaxPendingPerSender = 100
	// BatchMaxPerSenderPerSecond is the per-sender rate limit.
	BatchMaxPerSenderPerSecond = 20
	// BatchMaxConcurrent is the max number of batch calls running at once.
	BatchMaxConcurrent = 4
	// BatchRecentHashCacheSize is how many recent tx hashes are remembered
	// for cheap duplicate rejection.
	BatchRecentHashCacheSize = 100_000
)

// BatchTxResult is the per-transaction outcome of a batch call. A failed tx
// does not fail the batch: its Hash is zero and Error explains why.
type BatchTxResult struct {
	Hash  common.Hash `json:"hash"`
	Error string      `json:"error,omitempty"`
}

// batchRateLimiter holds the in-memory DoS-protection state for batch
// admission. All methods are safe for concurrent use.
type batchRateLimiter struct {
	mu sync.Mutex
	// sender -> timestamps of accepted txs within the last second.
	senderWindows map[common.Address][]time.Time
	// sender -> txs currently being inserted.
	senderPending map[common.Address]int
	// hashes seen recently (FIFO eviction) for cheap duplicate rejection.
	recentHashes map[common.Hash]struct{}
	recentOrder  []common.Hash
	// semaphore for concurrent batch calls.
	batchSem chan struct{}
}

func newBatchRateLimiter() *batchRateLimiter {
	return &batchRateLimiter{
		senderWindows: make(map[common.Address][]time.Time),
		senderPending: make(map[common.Address]int),
		recentHashes:  make(map[common.Hash]struct{}),
		batchSem:      make(chan struct{}, BatchMaxConcurrent),
	}
}

// acquireBatchSlot reserves one of the concurrent batch slots.
func (l *batchRateLimiter) acquireBatchSlot(ctx context.Context) (func(), error) {
	select {
	case l.batchSem <- struct{}{}:
		return func() { <-l.batchSem }, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

// checkSenderRate records one tx attempt for sender and rejects it when the
// per-second rate limit is exceeded.
func (l *batchRateLimiter) checkSenderRate(sender common.Address) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	now := time.Now()
	cutoff := now.Add(-time.Second)
	window := l.senderWindows[sender]
	kept := window[:0]
	for _, t := range window {
		if t.After(cutoff) {
			kept = append(kept, t)
		}
	}
	if len(kept) >= BatchMaxPerSenderPerSecond {
		l.senderWindows[sender] = kept
		return fmt.Errorf("rate limit exceeded for sender %s: max %d tx/second", sender.Hex(), BatchMaxPerSenderPerSecond)
	}
	l.senderWindows[sender] = append(kept, now)
	return nil
}

// tryBeginPending reserves one pending slot for sender.
func (l *batchRateLimiter) tryBeginPending(sender common.Address) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.senderPending[sender] >= BatchMaxPendingPerSender {
		return fmt.Errorf("too many pending transactions for sender %s: max %d", sender.Hex(), BatchMaxPendingPerSender)
	}
	l.senderPending[sender]++
	return nil
}

// endPending releases one pending slot for sender.
func (l *batchRateLimiter) endPending(sender common.Address) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.senderPending[sender] > 0 {
		l.senderPending[sender]--
	}
}

// isDuplicate reports whether hash was accepted recently.
func (l *batchRateLimiter) isDuplicate(hash common.Hash) bool {
	l.mu.Lock()
	defer l.mu.Unlock()

	_, ok := l.recentHashes[hash]
	return ok
}

// markSeen records a successfully submitted tx hash.
func (l *batchRateLimiter) markSeen(hash common.Hash) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if _, ok := l.recentHashes[hash]; ok {
		return
	}
	l.recentHashes[hash] = struct{}{}
	l.recentOrder = append(l.recentOrder, hash)
	if len(l.recentOrder) > BatchRecentHashCacheSize {
		oldest := l.recentOrder[0]
		l.recentOrder = l.recentOrder[1:]
		delete(l.recentHashes, oldest)
	}
}

// batchPreparedTx is one batch item after Phase A (parallel decode/recover).
type batchPreparedTx struct {
	idx      int
	hash     common.Hash
	sender   common.Address
	nonce    uint64
	cosmosTx sdk.Tx
	err      error
}

// prepareBatchTx runs the expensive per-tx admission work (RLP decode,
// sender recovery, basic validation, cosmos tx build). It is safe to run
// concurrently for different items: it touches no shared mutable state.
func (b *Backend) prepareBatchTx(data hexutil.Bytes, idx int) batchPreparedTx {
	if len(data) == 0 {
		return batchPreparedTx{idx: idx, err: errors.New("empty raw transaction")}
	}

	tx := &ethtypes.Transaction{}
	if err := tx.UnmarshalBinary(data); err != nil {
		return batchPreparedTx{idx: idx, err: fmt.Errorf("transaction decoding failed: %w", err)}
	}

	// Cheap pre-check before the expensive signature recovery: a negative
	// fee cap can never be valid. A zero fee cap IS valid on this chain
	// when the base fee is 0 (minimum-gas-prices 0, empty blocks), so it
	// must be accepted here exactly as the single-tx path accepts it; the
	// network base-fee floor is still enforced by the mempool insert.
	if feeCap := tx.GasFeeCap(); feeCap == nil || feeCap.Sign() < 0 {
		return batchPreparedTx{idx: idx, err: errors.New("gas fee cap must not be negative")}
	}

	// check the local node config in case unprotected txs are disabled
	if !b.UnprotectedAllowed() {
		if !tx.Protected() {
			return batchPreparedTx{idx: idx, err: errors.New("only replay-protected (EIP-155) transactions allowed over RPC")}
		}
		if tx.ChainId().Uint64() != b.EvmChainID.Uint64() {
			return batchPreparedTx{idx: idx, err: fmt.Errorf("incorrect chain-id; expected %d, got %d", b.EvmChainID, tx.ChainId())}
		}
	}

	cfg := b.ChainConfig()
	if cfg == nil {
		cfg = evmtypes.DefaultChainConfig(b.EvmChainID.Uint64()).EthereumConfig(nil)
	}
	ethSigner := ethtypes.LatestSigner(cfg)

	ethereumTx := &evmtypes.MsgEthereumTx{}
	if err := ethereumTx.FromSignedEthereumTx(tx, ethSigner); err != nil {
		return batchPreparedTx{idx: idx, err: fmt.Errorf("failed to convert ethereum transaction: %w", err)}
	}

	if err := ethereumTx.ValidateBasic(); err != nil {
		return batchPreparedTx{idx: idx, err: fmt.Errorf("failed to validate transaction: %w", err)}
	}

	baseDenom := evmtypes.GetEVMCoinDenom()
	cosmosTx, err := ethereumTx.BuildTx(b.ClientCtx.TxConfig.NewTxBuilder(), baseDenom)
	if err != nil {
		return batchPreparedTx{idx: idx, err: fmt.Errorf("failed to build cosmos tx: %w", err)}
	}

	return batchPreparedTx{
		idx:      idx,
		hash:     tx.Hash(),
		sender:   common.BytesToAddress(ethereumTx.From),
		nonce:    tx.Nonce(),
		cosmosTx: cosmosTx,
	}
}

// shardOf returns the admission shard for a sender (fnv hash, 16 shards).
func shardOf(sender common.Address) int {
	h := fnv.New32a()
	_, _ = h.Write(sender.Bytes())
	return int(h.Sum32() % BatchNumShards)
}

// SendRawTransactionBatch submits a batch of raw Ethereum transactions.
// Each transaction is processed independently: one failure does not fail
// the batch. Results are returned in the same order as the input.
func (b *Backend) SendRawTransactionBatch(ctx context.Context, data []hexutil.Bytes) (results []BatchTxResult, err error) {
	ctx, span := tracer.Start(ctx, "SendRawTransactionBatch")
	defer func() { evmtrace.EndSpanErr(span, err) }()
	span.SetAttributes(attribute.Int("batch_size", len(data)))

	if len(data) == 0 {
		return nil, errors.New("empty batch: at least one raw transaction is required")
	}
	if len(data) > MaxBatchTxs {
		return nil, fmt.Errorf("batch too large: %d transactions, max %d", len(data), MaxBatchTxs)
	}
	totalBytes := 0
	for _, d := range data {
		totalBytes += len(d)
	}
	if totalBytes > MaxBatchBytes {
		return nil, fmt.Errorf("batch too large: %d bytes, max %d", totalBytes, MaxBatchBytes)
	}

	limiter := b.batchLimiter
	if limiter == nil {
		// Backend built without NewBackend (e.g. in tests): fall back to a
		// fresh limiter instead of failing the call.
		limiter = newBatchRateLimiter()
	}

	release, err := limiter.acquireBatchSlot(ctx)
	if err != nil {
		return nil, err
	}
	defer release()

	// Phase A — parallel decode + sender recovery + build.
	prepared := make([]batchPreparedTx, len(data))
	workers := 2 * runtime.NumCPU()
	if workers > 32 {
		workers = 32
	}
	if workers < 1 {
		workers = 1
	}
	sem := make(chan struct{}, workers)
	var wg sync.WaitGroup
	for i, raw := range data {
		i, raw := i, raw
		wg.Add(1)
		go func() {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			prepared[i] = b.prepareBatchTx(raw, i)
		}()
	}
	wg.Wait()

	// Phase B — group by sender, sort by nonce, shard by sender hash.
	results = make([]BatchTxResult, len(data))
	bySender := make(map[common.Address][]*batchPreparedTx)
	for i := range prepared {
		p := &prepared[i]
		if p.err != nil {
			results[p.idx] = BatchTxResult{Error: p.err.Error()}
			continue
		}
		if limiter.isDuplicate(p.hash) {
			results[p.idx] = BatchTxResult{Error: "duplicate transaction"}
			continue
		}
		if err := limiter.checkSenderRate(p.sender); err != nil {
			results[p.idx] = BatchTxResult{Error: err.Error()}
			continue
		}
		if err := limiter.tryBeginPending(p.sender); err != nil {
			results[p.idx] = BatchTxResult{Error: err.Error()}
			continue
		}
		bySender[p.sender] = append(bySender[p.sender], p)
	}

	// Within one sender, sort by nonce and reject duplicate nonces in the
	// same batch (the second one would fail at insert anyway).
	shardGroups := make([][][]*batchPreparedTx, BatchNumShards)
	for sender, items := range bySender {
		sort.Slice(items, func(a, c int) bool { return items[a].nonce < items[c].nonce })
		seenNonce := make(map[uint64]bool)
		kept := items[:0]
		for _, it := range items {
			if seenNonce[it.nonce] {
				results[it.idx] = BatchTxResult{Error: fmt.Sprintf("duplicate nonce %d in batch", it.nonce)}
				limiter.endPending(sender)
				continue
			}
			seenNonce[it.nonce] = true
			kept = append(kept, it)
		}
		if len(kept) == 0 {
			continue
		}
		shardGroups[shardOf(sender)] = append(shardGroups[shardOf(sender)], kept)
	}

	// One goroutine per non-empty shard; inside a shard, senders are
	// submitted sequentially and each sender's txs in nonce order.
	for _, groups := range shardGroups {
		if len(groups) == 0 {
			continue
		}
		groups := groups
		wg.Add(1)
		go func() {
			defer wg.Done()
			for _, group := range groups {
				senderFailed := false
				for _, it := range group {
					if senderFailed {
						results[it.idx] = BatchTxResult{Error: fmt.Sprintf("held: preceding transaction from %s failed", it.sender.Hex())}
						limiter.endPending(it.sender)
						continue
					}
					if err := b.Mempool.Insert(ctx, it.cosmosTx); err != nil {
						results[it.idx] = BatchTxResult{Error: err.Error()}
						senderFailed = true
					} else {
						results[it.idx] = BatchTxResult{Hash: it.hash}
						limiter.markSeen(it.hash)
						b.TrackTxIfSupported(it.hash)
					}
					limiter.endPending(it.sender)
				}
			}
		}()
	}
	wg.Wait()

	return results, nil
}
