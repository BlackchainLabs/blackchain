# BLACKCHAIN — Identitas EVM/BKC (keputusan Sesi 4, 2026-11-20)

## Keputusan

| Item | Lama (Jalur A awal) | Baru (identitas BKC) |
|---|---|---|
| EVM chain ID | 262144 (0x40000, default Cosmos EVM) | **20261120** (0x1352C10) |
| CometBFT chain-id | `blackchain-1` | **`blackchain_20261120-1`** |
| Base denom (gas token) | `stake` | **`abkc`** (atto BKC) |
| Display | BKC, 18 desimal | BKC, 18 desimal (tidak berubah) |
| 1 BKC | 10^18 stake | 10^18 abkc |

## Mengapa berubah

1. **262144 bentrok.** Menurut registry ethereum-lists/chains
   (2.894 chain, diperiksa 2026-11-20 via `chainid.network/chains.json`),
   chain ID 262144 sudah terdaftar sebagai **"MPCQ Mainnet"**. Memakainya
   berarti transaksi BKC bisa di-replay/dikacaukan dengan chain lain —
   persis yang dicegah EIP-155.
2. **20261120 tidak terdaftar.** Hasil yang sama: `20261120 -> NOT
   REGISTERED`. Angka ini diambil dari tanggal peluncuran proyek
   (20 Nov 2026), mudah diingat, dan tidak bentrok dengan chain yang
   dikenal (9000/9001 = Evmos — dihindari; 1337 = Geth Testnet — hanya
   devnet lokal; 31337, 7777777 Zora, 4663 Robinhood, 5042 Arc, 99901
   Elysium — semuanya berbeda).
3. **Denom `stake` bukan identitas BKC.** Tokenomics menetapkan native
   coin BKC; base denom EVM harus `abkc` (atto BKC) agar saldo EVM
   (wei) = saldo bank (abkc) dengan display BKC 18 desimal, konsisten
   dengan `bank.denom_metadata` yang sudah ada sejak genesis pertama.

## Implementasi (kode)

Salinan kerja: `build/blackchain-sdk54-bkc/` (salinan Jalur A;
tree `build/blackchain-sdk54/` yang sudah jalan TIDAK diubah).

- `app/app.go`: `var evmChainID = uint64(20261120)` — diteruskan ke
  `evmkeeper.NewKeeper(...)`; keeper memanggil
  `types.DefaultChainConfig(evmChainID)` (cosmos/evm v0.7.4
  `x/vm/keeper/keeper.go:124`), sehingga ChainConfig EVM, JSON-RPC
  `eth_chainId`, dan penandatanganan EIP-155 semuanya memakai 20261120.
- `app/config.go`: `sdk.DefaultBondDenom = "abkc"` — dipakai scaffold
  untuk staking/mint/gov default.
- Genesis (diperbarui sebelum `gentx`/`validate-genesis`):
  `evm.params.evm_denom = "abkc"`,
  `evm.params.extended_denom_options.extended_denom = "abkc"`,
  `staking.params.bond_denom = "abkc"`, `mint.params.mint_denom = "abkc"`,
  `gov.params.min_deposit[].denom = "abkc"`,
  `bank.denom_metadata`: base `abkc` / display `BKC` (exponent 18),
  saldo akun dan supply dalam `abkc`.

## Devnet identitas baru

- Binary: `build/blackchaind-sdk54-bkc`
- Home: `devnet-data-bkc/cosmos`
- Chain-id: `blackchain_20261120-1`
- Port (digeser agar tidak bentrok dengan devnet lama yang masih jalan):
  CometBFT RPC 26677, P2P 26676, gRPC 9102, REST 1328, pprof 6071,
  EVM JSON-RPC 8555, WS 8556.
- Start: `blackchaind-sdk54-bkc start --home <home> --minimum-gas-prices 0abkc
  --rpc.laddr tcp://127.0.0.1:26677 --p2p.laddr tcp://127.0.0.1:26676
  --grpc.address 127.0.0.1:9102 --rpc.pprof_laddr 127.0.0.1:6071
  --json-rpc.enable=true --json-rpc.address 127.0.0.1:8555
  --json-rpc.ws-address 127.0.0.1:8556`
  (+ `config.toml` mempool.type="app" untuk mempool Krakatoa,
  seperti devnet SDK54 lama.)

## Bukti yang harus ada (diisi setelah start)

- `eth_chainId` -> `0x1352c10` (20261120)
- `eth_blockNumber` cocok dengan height CometBFT 26677
- Satu transfer EVM: dari alamat ETH validator ke penerima sekali pakai,
  nilai dan saldo sebelum/sesudah terverifikasi (seperti bukti
  `docs/cosmos-devnet-sdk54-first-blocks-2026-11-20.txt`).
- Devnet lama (262144/stake, port 8545/26667, PID 3219) tetap jalan
  sebagai arsip Jalur A dan TIDAK dipakai untuk benchmark baru.

## Catatan kehati-hatian

- Chain ID 20261120 adalah pilihan devnet/testnet. Sebelum mainnet,
  daftarkan chain ini ke ethereum-lists/chains (PR ke repo
  ethereum-lists/chains) agar dompet/explorer mengenalinya — itu langkah
  publikasi, bukan langkah teknis, dan butuh persetujuan pemilik.
- Mengganti chain ID setelah mainnet = chain baru; keputusan ini final
  untuk testnet. Bila pemilik ingin nomor lain, ubah SEKARANG sebelum
  testnet publik, bukan sesudahnya.
