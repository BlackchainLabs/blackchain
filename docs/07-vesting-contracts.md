# BLACKCHAIN — Spesifikasi Kontrak Vesting & Claim BKC v0.1

**Status: SPEC + KODE + TEST — BELUM DIAUDIT, BELUM DI-DEPLOY**

- Tanggal: 20 Nov 2026 (diperbarui: refactor OpenZeppelin, 20 Nov 2026)
- Penulis: Vesting Contracts AI (subagent)
- Lokasi kode: `repo/smart-contracts/vesting/` (kerja lokal saja; **tidak di-push ke GitHub**)
- Toolchain: Foundry 1.10.0, solc 0.8.20, pragma `^0.8.20`, SPDX MIT
- Dependensi: **OpenZeppelin Contracts v5.7.0** (submodule `repo/lib/openzeppelin-contracts`,
  rev `cab19933`, disetujui pemilik 20 Nov 2026 — lihat §9)
- **Belum diaudit** — baca §7 (risiko) sebelum keputusan deploy apa pun.
- **Tidak ada deploy ke chain apa pun** dalam pekerjaan ini. Tidak ada seed
  phrase / private key yang diminta, dipakai, atau disimpan.

## 0. Ringkasan

| Kontrak | Fungsi |
|---|---|
| `BKC.sol` | ERC-20 BKC, max supply tetap 1.000.000.000 BKC, 18 desimal |
| `TeamVesting.sol` | Vesting alokasi tim 50.000.000 BKC (5%), satu beneficiary |
| `CommunityClaim.sol` | Klaim airdrop komunitas berbasis Merkle proof, sekali per alamat, pausable |

Tokenomics yang dipakai (dari `docs/04-tokenomics.md`, konsisten):

| Alokasi | BKC | Unit terkecil (1 BKC = 10^18) |
|---|---|---|
| Komunitas (95%) | 950.000.000 | 9,5 × 10^26 |
| Tim dev (5%) | 50.000.000 | 5 × 10^25 |
| **Total max supply** | **1.000.000.000** | **1 × 10^27** |

Base denom EVM: `abkc` (1 BKC = 10^18 abkc). Di mainnet, coin native
hidup di Cosmos bank module; `BKC.sol` adalah representasi ERC-20 di sisi
EVM untuk kontrak vesting/claim. **Pemetaan bank `abkc` ↔ ERC-20 ini
belum dirancang dan di luar cakupan dokumen ini** — butuh keputusan pemilik
(lihat §8, keputusan #5).

## 1. Kontrak BKC (`src/BKC.sol`)

ERC-20 berbasis **OpenZeppelin v5.7.0** (`ERC20`).

- `name` = `"Blackchain"`, `symbol` = `"BKC"`, `decimals` = 18 (default OZ).
- `MAX_SUPPLY = 1_000_000_000 * 10**18` — tetap, tidak bisa diubah.
- Constructor: `constructor(address initialHolder)` mencetak seluruh supply
  ke `initialHolder` sekali via `_mint`. **Tidak ada fungsi mint setelah itu**,
  tidak ada burn, tidak ada pause, tidak ada peran admin pada token.
- `initialHolder` pada produksi **harus** alamat treasury/distribusi yang
  dipilih pemilik (multisig direkomendasikan). Alamat ini yang kemudian
  mendanai `TeamVesting` (50 jt BKC) dan `CommunityClaim` (sesuai pool
  airdrop) lewat `transfer` biasa.
- Fungsi: `transfer`, `approve`, `transferFrom`, `balanceOf`,
  `allowance`, `totalSupply` — semuanya implementasi OZ `ERC20`.
  Error kegagalan dari OZ (`ERC20InsufficientBalance`,
  `ERC20InvalidReceiver`, dll., lihat `draft-IERC6093.sol`).
- Aritmetika Solidity 0.8.20 (checked math bawaan).

## 2. TeamVesting (`src/TeamVesting.sol`) — skema vesting tim

### 2.1 Parameter (diputuskan di sini, dicatat alasannya)

| Parameter | Nilai | Keterangan |
|---|---|---|
| Alokasi | 50.000.000 BKC | 5% max supply, sesuai tokenomics |
| `start` | parameter constructor | dimaksudkan = waktu mainnet launch (timestamp Unix) |
| Cliff | 90 hari (3 × 30 hari) | `CLIFF_DURATION = 90 days` |
| Durasi total | 360 hari (12 × 30 hari) | `VESTING_DURATION = 360 days` |
| Jendela linear | 270 hari | `LINEAR_DURATION = 270 days` (360 − 90) |

**Rumus vested** (`vestedAmount(timestamp)`):

- `timestamp < start + 90 hari` → **0**
- `start + 90 hari ≤ timestamp < start + 360 hari` →
  `totalAllocation × (timestamp − (start + 90 hari)) / 270 hari`
- `timestamp ≥ start + 360 hari` → `totalAllocation` (penuh, di-cap)

**Alasan cliff 3 bulan lalu linear 9 bulan** (bukan linear 12 bulan penuh
tanpa cliff, bukan cliff 12 bulan lalu lump-sum):

1. Sesuai usulan tokenomics (`docs/04-tokenomics.md` §4: "Cliff: 3 bulan
   setelah mainnet; linear vesting: 12 bulan total sejak mainnet").
2. Cliff menunda unlock pertama sehingga tim tidak menerima apa pun di
   3 bulan pertama pasca-mainnet — insentif untuk tetap membangun.
3. Linear 9 bulan setelah cliff (bukan lump-sum di bulan 12) menghindari
   dump sekali besar di satu tanggal; pelepasan berjalan halus per detik
   (`block.timestamp`).
4. Total tetap 12 bulan, jadi tidak mengubah janji tokenomics.

**Bulan = 30 hari tetap.** Kalender bervariasi (28–31 hari), jadi kontrak
memakai hitungan hari tetap berbasis `block.timestamp` agar jadwal
deterministik dan dapat diverifikasi siapa pun. Ini asumsi eksplisit (§7).

### 2.2 Beneficiary — parameter, bukan alamat hardcode

- `beneficiary` adalah **parameter constructor** yang diisi pemilik saat
  deploy (alamat multisig/treasury tim yang sesungguhnya).
- **Alamat `0x000000000000000000000000000000000000dEaD` TIDAK boleh dipakai
  sebagai beneficiary** — itu alamat burn; token yang dikirim ke sana
  hilang permanen. Kontrak menolak `address(0)` sebagai beneficiary,
  dan spesifikasi ini melarang pemakaian alamat burn/placeholder apa pun.
- Alamat beneficiary yang sesungguhnya **belum diputuskan** — lihat §8,
  keputusan #1. Tidak ada alamat beneficiary yang ditulis di dokumen ini
  selain placeholder test (alamat `0x1111…` hanya di test, bukan produksi).

### 2.3 Fungsi & peran

| Fungsi | Siapa | Perilaku |
|---|---|---|
| `constructor(token, beneficiary, owner, start, totalAllocation)` | deployer | Set semua parameter immutable |
| `vestedAmount(ts)` (view) | siapa pun | Jumlah vested pada waktu `ts` (rumus §2.1) |
| `releasableAmount()` (view) | siapa pun | `vestedAmount(now) − released` |
| `release()` | **siapa pun** | Kirim semua yang sudah vested & belum dirilis ke `beneficiary`. Revert `NothingToRelease` bila 0 — ini guard anti double-release: panggilan kedua langsung setelah yang pertama selalu revert karena tidak ada yang baru vested |
| `revoke()` | **owner saja** | Lihat §2.4 |

- Pendanaan: owner harus `transfer` 50 jt BKC ke kontrak setelah deploy.
  Kontrak tidak menarik dana sendiri.
- `release()` sengaja bisa dipanggil siapa pun (pola standar vesting):
  dana selalu mengalir ke `beneficiary`, jadi pemanggil tidak bisa
  mengalihkan dana. State `released` di-update **sebelum** transfer
  (checks-effects-interactions), event di-emit sebelum transfer, dan
  fungsi dilindungi `nonReentrant` (OpenZeppelin `ReentrancyGuard`).
- Admin memakai OpenZeppelin `Ownable`: `owner` di-set di constructor dan
  bisa diputar via `transferOwnership` (owner saja). **Jangan
  `renounceOwnership` selama vesting aktif** — `revoke()` akan menjadi
  tidak bisa dipanggil selamanya.
- Event: `TokensReleased(beneficiary, amount)`, `VestingRevoked(owner, amountReturned)`,
  plus `OwnershipTransferred` (OZ, saat owner diputar).
- Error kustom: `NothingToRelease`, `AlreadyRevoked`, `RevokeAfterCliff`,
  `ZeroBeneficiary`, `ZeroToken`. Error owner bukan dari OZ:
  `OwnableUnauthorizedAccount(account)` (bila bukan owner),
  `OwnableInvalidOwner` (constructor dengan owner nol).

### 2.4 Revocable — hanya sebelum cliff

- `revoke()` hanya bisa dipanggil **owner**, dan hanya **sebelum cliff**
  (`block.timestamp < start + 90 hari`). Efek: `revoked = true`,
  seluruh saldo kontrak dikembalikan ke owner, `release()` selamanya
  revert (`AlreadyRevoked`).
- **Setelah cliff, revoke revert (`RevokeAfterCliff`) — jadwal menjadi
  irrevocable.** Ini disengaja: setelah tim mulai vesting, satu kunci
  owner tidak boleh memotong hak tim di tengah jalan.
- Konsekuensi yang harus dipahami pemilik: bila tim bermasalah setelah
  cliff, tidak ada jalan kontraktual untuk menghentikan vesting — itu
  keputusan desain, bukan bug. Bila pemilik menginginkan revocable penuh,
  itu perubahan spesifikasi (butuh kontrak baru + audit ulang).

## 3. CommunityClaim (`src/CommunityClaim.sol`) — skema claim komunitas

Merkle-airdrop style untuk bagian dari alokasi komunitas 95%. Pool airdrop
yang diusulkan tokenomics adalah 200 jt BKC (20% total supply, §3
`04-tokenomics.md`) — **jumlah pool final belum diputuskan** (§8 #4);
kontrak ini netral terhadap jumlah: owner mendanai kontrak sejumlah yang
dibutuhkan untuk root yang aktif.

### 3.1 Konstruksi Merkle tree (kontrak & off-chain HARUS sama persis)

- Leaf: `leaf = keccak256(abi.encodePacked(account, amount))`,
  `amount` dalam unit terkecil BKC (1 BKC = 10^18).
- Hash pasangan **terurut (sorted-pair)**: di tiap level, dari dua node
  `a, b`, hash `keccak256(abi.encodePacked(min(a,b), max(a,b)))`.
  Ini sama dengan aturan `MerkleProof` OpenZeppelin untuk tree terurut.
- Verifikasi di kontrak memakai **OpenZeppelin `MerkleProof.verifyCalldata`**
  (variabel calldata yang hemat gas dari `MerkleProof.verify`).
  Kontrak tidak lagi memakai fungsi `_verify` tulisan sendiri.
- **Builder off-chain harus memakai aturan yang sama.** Contoh Python
  (bukan bagian kontrak, hanya referensi builder):

```python
from eth_hash.auto import keccak  # atau hashlib.sha3_256 TIDAK sama; pakai keccak-256
def leaf(addr: str, amount: int) -> bytes:
    return keccak(bytes.fromhex(addr[2:]) + amount.to_bytes(32, "big"))
def pair(a: bytes, b: bytes) -> bytes:
    x, y = (a, b) if a <= b else (b, a)
    return keccak(x + y)
# tree: gabungkan level demi level dengan pair(); root = satu hash terakhir.
# proof untuk satu leaf = saudara di tiap level, dari bawah ke atas.
```

  Perhatian: `abi.encodePacked(account, amount)` = 20 byte alamat +
  32 byte amount big-endian. Jangan pakai `abi.encode` (padding berbeda)
  dan jangan double-hash leaf.

### 3.2 Fungsi & peran

| Fungsi | Siapa | Perilaku |
|---|---|---|
| `constructor(token, owner, merkleRoot)` | deployer | `merkleRoot` awal boleh `bytes32(0)` bila tree belum siap — klaim tidak akan lolos sampai root di-set |
| `claim(amount, proof)` | pemohon (msg.sender) | Sekali per alamat; cek `claimed`, `amount > 0`, proof valid; tandai claimed **sebelum** transfer; transfer `amount` ke pemohon |
| `setMerkleRoot(newRoot)` | **owner saja** | Ganti root; event `MerkleRootUpdated(oldRoot, newRoot)` |
| `pause()` / `unpause()` | **owner saja** | `pause` memblokir klaim baru; tidak membekukan token yang sudah diklaim; `setMerkleRoot` tetap bisa dipanggil saat pause |
| `recoverRemaining(to, amount)` | **owner saja** | Tarik token yang belum diklaim (mis. setelah kampanye selesai); event `RemainingRecovered` |

- Anti double-claim: mapping `claimed[account]`; klaim kedua revert
  `AlreadyClaimed`. **Root update tidak me-reset `claimed`** — alamat
  yang sudah klaim tetap tidak bisa klaim lagi walau root diganti (diuji,
  §8 test `testRootUpdateDoesNotReEnableDoubleClaim`).
- Risiko root update: owner bisa mengganti siapa yang eligible ke depan.
  Karena itu root update butuh tata kelola yang sama seriusnya dengan
  pergerakan dana (multisig/timelock, diumumkan dulu) — lihat §7.
- Pause memakai OpenZeppelin `Pausable`: `pause()`/`unpause()` owner-only
  (memanggil `_pause()`/`_unpause()` internal), `paused()` view publik,
  klaim yang diblokir revert `EnforcedPause()`. `setMerkleRoot` tetap bisa
  dipanggil saat pause (diuji).
- `claim()` dan `recoverRemaining()` dilindungi `nonReentrant`
  (OpenZeppelin `ReentrancyGuard`).
- Event: `Claimed(account, amount)`, `MerkleRootUpdated(oldRoot, newRoot)`,
  `Paused(account)`, `Unpaused(account)` (keduanya event OZ, argumen tidak
  di-index), `RemainingRecovered(to, amount)`, plus `OwnershipTransferred` (OZ).
- Error kustom: `AlreadyClaimed`, `InvalidProof`, `ZeroAmount`,
  `ZeroToken`. Error OZ: `OwnableUnauthorizedAccount(account)` (bukan
  owner), `EnforcedPause()` (klaim saat pause).

## 4. Peran owner / admin

| Peran | Dipegang oleh | Kekuasaan |
|---|---|---|
| Owner `TeamVesting` | alamat `owner` (constructor) | `revoke()` hanya sebelum cliff |
| Owner `CommunityClaim` | alamat `owner` (constructor) | `setMerkleRoot`, `pause`/`unpause`, `recoverRemaining` |
| Beneficiary vesting | alamat `beneficiary` (constructor) | Menerima token; **tidak** punya fungsi admin |
| Pemohon klaim | siapa pun di tree | `claim()` untuk dirinya sendiri saja |
| Deployer BKC | `initialHolder` | Menerima seluruh supply; mendanai kedua kontrak |

**Rekomendasi (belum diputuskan — §8 #2):** semua peran owner dipegang
multisig (mis. tim inti + pengawas) dan, untuk mainnet, di belakang
timelock. Satu kunci EOA sebagai owner adalah risiko sentralisasi yang
diketahui dan dicatat di §7.

## 5. Event (ringkas, untuk indexer/dashboard)

- BKC: `Transfer(from, to, value)`, `Approval(owner, spender, value)` (OZ ERC20).
- TeamVesting: `TokensReleased(beneficiary, amount)`,
  `VestingRevoked(owner, amountReturned)`, `OwnershipTransferred` (OZ).
- CommunityClaim: `Claimed(account, amount)`,
  `MerkleRootUpdated(oldRoot, newRoot)`, `Paused(account)`,
  `Unpaused(account)` (OZ), `RemainingRecovered(to, amount)`,
  `OwnershipTransferred` (OZ).

## 6. File yang dibuat

```
repo/smart-contracts/vesting/
├── foundry.toml                 # src=src, test=test, solc 0.8.20,
│                                # remapping @openzeppelin/contracts/ ke
│                                # ../../lib/openzeppelin-contracts/contracts/
│                                # + allow_paths untuk direktori itu
├── src/
│   ├── BKC.sol                  # ERC-20 di atas OZ ERC20
│   ├── TeamVesting.sol          # OZ Ownable + ReentrancyGuard
│   └── CommunityClaim.sol       # OZ Ownable + Pausable + ReentrancyGuard
│                                # + MerkleProof.verifyCalldata
└── test/
    ├── Vm.sol                   # 19 baris — interface cheatcode minimal lokal (tanpa forge-std)
    ├── TeamVesting.t.sol        # BKC (6 test) + TeamVesting (15 test)
    └── CommunityClaim.t.sol     # CommunityClaim (16 test)
```

Juga diubah: `repo/smart-contracts/README.md` (menunjuk ke `vesting/`).
`repo/lib/openzeppelin-contracts/` adalah submodule git (v5.7.0,
rev `cab19933`); `foundry.lock` di root repo mengunci tag itu.
**Tidak diubah:** `00-mission-log.md` (induk yang mengintegrasikan).

## 7. Risiko & asumsi — BACA SEBELUM DEPLOY

**Status: BELUM DIAUDIT. Kode ini belum diperiksa auditor independen.
Jangan deploy ke mainnet — bahkan ke testnet publik — sebelum review
Security Auditor AI dan audit eksternal bila memungkinkan.**

### Risiko

1. **Owner terpusat.** Owner kedua kontrak bisa revoke (sebelum cliff),
   mengganti Merkle root, pause, dan menarik sisa dana klaim. Bila kunci
   owner bocor/dikuasai satu orang, dana & eligibility bisa disalahgunakan.
   Mitigasi yang diusulkan: multisig + timelock + pengumuman sebelum
   perubahan root/recovery (belum diimplementasikan).
2. **Merkle root salah / tree builder tidak cocok.** Bila tree off-chain
   dibangun dengan aturan berbeda (mis. `abi.encode` bukan
   `abi.encodePacked`, atau pair tidak terurut), **semua** klaim gagal.
   Mitigasi: uji root + proof di testnet dengan data asli sebelum
   pengumuman; publikasikan builder & daftar leaf.
3. **Eligibility & anti-Sybil di luar kontrak.** Kontrak hanya memeriksa
   proof; siapa yang masuk tree adalah keputusan off-chain. Kriteria
   anti-Sybil belum dirancang (Month 2, lihat tokenomics §5).
4. **Dana kontrak tidak cukup.** Bila owner mendanai kurang dari total
   klaim/vesting, klaim/transfer gagal di tengah jalan. Cek saldo kontrak
   sebelum membuka klaim (saldo ≥ total alokasi root aktif).
5. **`block.timestamp` bisa dimanipulasi validator dalam batas kecil**
   (beberapa detik). Tidak material untuk jadwal bulanan, tapi dicatat —
   `forge build` juga memberi peringatan lint untuk ini (satu-satunya
   peringatan lint yang tersisa setelah refactor).
6. **Peringatan lint `forge build` (bukan error):** hanya `block-timestamp`
   (butir 5). Peringatan `reentrancy-events` dan `non-reentrant-not-first`
   dari versi self-contained sudah hilang: semua fungsi yang mentransfer
   dana kini memakai `nonReentrant` (modifier pertama), state di-update
   dan event di-emit **sebelum** external call — bila transfer gagal,
   seluruh transaksi revert termasuk event-nya, jadi urutan ini aman.
7. **Pemetaan `abkc` (bank) ↔ ERC-20 belum ada.** Kontrak ini berasumsi
   BKC ERC-20 adalah representasi yang sah; tanpa bridge/mapping resmi,
   token ini bisa menjadi token kedua yang membingungkan supply.
8. **Tidak ada upgrade path.** Kontrak tidak upgradeable. Bug = deploy
   ulang + migrasi dana (butuh owner). Ini disengaja demi kesederhanaan
   dan auditabilitas.
9. **Revocable hanya sebelum cliff** (§2.4) — setelah cliff tidak ada jalan
   kontraktual menghentikan vesting tim.
10. **Owner OZ bisa diputar dan (secara teknis) di-renounce.**
    `transferOwnership` memungkinkan rotasi owner — bagus untuk migrasi
    ke multisig. Tapi `renounceOwnership` akan membuat `revoke()`,
    `setMerkleRoot`, `pause`, dan `recoverRemaining` tidak bisa dipanggil
    selamanya. Jangan pernah renounce selama vesting/klaim aktif.
11. **Dependensi OpenZeppelin.** Kontrak kini bergantung pada OZ v5.7.0
    (submodule, rev `cab19933`, dikunci `foundry.lock`). Bila submodule
    tidak ter-clone (mis. clone tanpa `--recursive`), build gagal — baca
    §9 untuk cara clone yang benar.

### Asumsi eksplisit

- Bulan = 30 hari tetap (§2.1). `start` = waktu mainnet launch.
- Alokasi tim tepat 50.000.000 BKC; kontrak tidak memaksa angka itu
  (parameter `totalAllocation`), deployer wajib memverifikasi.
- Satu beneficiary tim (bukan daftar). Bila tim perlu banyak penerima,
  deploy satu `TeamVesting` per penerima atau ubah spesifikasi.
- Klaim komunitas satu kali per alamat; tidak ada vesting pada klaim
  (langsung penuh saat klaim).
- Tidak ada pajak/fee pada transfer/klaim.
- Rantai target EVM-kompatibel (Cosmos EVM / Sepolia untuk uji).

## 8. Hasil test — dijalankan, bukan dikarang

Perintah (dijalankan 20 Nov 2026 di
`~/workspace/blackchain/repo/smart-contracts/vesting/`):

```bash
export PATH="$HOME/.foundry/bin:$PATH"
forge test
```

Toolchain: `forge 1.10.0` (commit `083e229941`, build 2026-11-19),
diinstal via `foundryup` (`curl -L https://foundry.paradigm.xyz | bash`
lalu `foundryup`); solc 0.8.20 (diunduh otomatis oleh forge).

**Hasil akhir setelah refactor OpenZeppelin: 37 test lolos, 0 gagal,
0 dilewati** (3 suite; sebelumnya 30/30 sebelum refactor):

```
Ran 6 tests for test/TeamVesting.t.sol:BKCTest
Suite result: ok. 6 passed; 0 failed; 0 skipped
Ran 15 tests for test/TeamVesting.t.sol:TeamVestingTest
Suite result: ok. 15 passed; 0 failed; 0 skipped
Ran 16 tests for test/CommunityClaim.t.sol:CommunityClaimTest
Suite result: ok. 16 passed; 0 failed; 0 skipped
Ran 3 test suites in 5.87ms (6.13ms CPU time): 37 tests passed, 0 failed, 0 skipped (37 total tests)
```

Rincian cakupan (semua yang diminta tugas, terpenuhi):

| # | Test | Status |
|---|---|---|
| BKC-1 | `testMaxSupplyMintedToDeployer` — supply 1 miliar BKC, 18 desimal | PASS |
| BKC-2 | `testTransferMovesBalance` | PASS |
| BKC-3 | `testTransferMoreThanBalanceReverts` — kini error OZ `ERC20InsufficientBalance` | PASS |
| BKC-4 | `testTokenNameSymbolDecimals` — BARU (OZ) | PASS |
| BKC-5 | `testApproveAndTransferFrom` — BARU (OZ) | PASS |
| BKC-6 | `testTransferToZeroAddressReverts` — error OZ `ERC20InvalidReceiver`, BARU | PASS |
| TV-1 | `testZeroVestedBeforeCliff` — vested 0 sebelum cliff | PASS |
| TV-2 | `testZeroVestedExactlyAtCliff` — vested 0 tepat di cliff (90 hari) | PASS |
| TV-3 | `testReleaseBeforeCliffReverts` | PASS |
| TV-4 | `testPartialVestedAfterCliff` — 1/3 vested di hari ke-180 | PASS |
| TV-5 | `testPartialReleasePaysBeneficiary` | PASS |
| TV-6 | `testDoubleReleaseRejected` — release ganda ditolak | PASS |
| TV-7 | `testFullVestedAfter12Months` — penuh di hari ke-360 | PASS |
| TV-8 | `testFullReleaseAfter12Months` + release susulan ditolak | PASS |
| TV-9 | `testVestedNeverExceedsTotal` — cap di 2 tahun | PASS |
| TV-10 | `testRevokeBeforeCliffReturnsFunds` | PASS |
| TV-11 | `testReleaseAfterRevokeReverts` | PASS |
| TV-12 | `testRevokeAfterCliffReverts` | PASS |
| TV-13 | `testOnlyOwnerCanRevoke` — kini error OZ `OwnableUnauthorizedAccount` | PASS |
| TV-14 | `testReleaseCallableByAnyonePaysBeneficiary` | PASS |
| TV-15 | `testOwnerCanTransferOwnership` — BARU (OZ Ownable) | PASS |
| CC-1 | `testClaimSucceedsWithValidProof` | PASS |
| CC-2 | `testDoubleClaimRejected` — klaim ganda ditolak | PASS |
| CC-3 | `testWrongProofRejected` — proof salah ditolak | PASS |
| CC-4 | `testWrongAmountRejected` — amount tidak cocok leaf ditolak | PASS |
| CC-5 | `testNonEligibleAddressRejected` | PASS |
| CC-6 | `testZeroAmountRejected` | PASS |
| CC-7 | `testOnlyOwnerCanSetRoot` — kini error OZ `OwnableUnauthorizedAccount` | PASS |
| CC-8 | `testSetRootByOwnerEnablesNewClaim` | PASS |
| CC-9 | `testRootUpdateDoesNotReEnableDoubleClaim` | PASS |
| CC-10 | `testPauseBlocksClaimAndUnpauseAllows` — kini error OZ `EnforcedPause`, BARU diperbarui | PASS |
| CC-11 | `testOnlyOwnerCanPause` — kini error OZ `OwnableUnauthorizedAccount` | PASS |
| CC-12 | `testOnlyOwnerCanUnpause` — kini error OZ `OwnableUnauthorizedAccount` | PASS |
| CC-13 | `testOnlyOwnerCanRecoverRemaining` — kini error OZ `OwnableUnauthorizedAccount` | PASS |
| CC-14 | `testSetRootWhilePausedAllowed` — BARU | PASS |
| CC-15 | `testRecoverRemainingTransfersToOwner` — BARU | PASS |
| CC-16 | `testRecoverRemainingZeroRecipientReverts` — BARU | PASS |

**Catatan perbaikan selama pengujian (dicatat jujur, bukan disembunyikan):**
dua kegagalan awal diperbaiki sebelum hasil akhir di atas — (a) interface
cheatcode lokal pertama memakai alamat turunan keccak yang salah sehingga
semua panggilan `vm.*` revert; diperbaiki ke alamat cheatcode Foundry
yang benar `0x7109709ECfa91a80626fF3989D68f67F5b1DD12D`; (b) satu test
`expectRevert` gagal karena `totalSupply()` di dalam argumen transfer
ikut terhitung sebagai "next call" — diperbaiki dengan menghitung jumlah
dulu ke variabel lokal. Setelah perbaikan, `forge test` diulang dan
menghasilkan 30/30 lolos seperti di atas. `forge build` lolos dengan
peringatan lint saja (lihat §7 butir 5–6).

**Catatan perbaikan selama refactor OpenZeppelin (20 Nov 2026):**
- **F30** — `forge build` gagal: remapping `../../lib/...` keluar dari
  direktori yang diizinkan solc ("File outside of allowed directories").
  Perbaikan: tambah `allow_paths = ["../../lib/openzeppelin-contracts"]`
  di `foundry.toml` (opsi standar Foundry untuk ini). Build lolos.
- **F31** — `forge build` memberi 3 peringatan `non-reentrant-not-first`
  (modifier `nonReentrant` bukan yang pertama) dan 4 peringatan
  `reentrancy-events` (event di-emit setelah external call). Perbaikan:
  `nonReentrant` dijadikan modifier pertama di semua fungsi terkait, dan
  event dipindah ke sebelum external call (aman: bila transfer gagal,
  seluruh transaksi revert termasuk event-nya). Setelah perbaikan,
  satu-satunya peringatan lint yang tersisa adalah `block-timestamp`
  (§7 butir 5). Tidak ada test yang dikurangi untuk memaksa lolos —
  sebaliknya 7 test baru ditambahkan (BKC-4/5/6, TV-15, CC-14/15/16)
  sehingga total naik 30 → **37 test, semua lolos**.

Menjalankan ulang: `cd repo/smart-contracts/vesting && forge test`
(dari workspace misi). Tidak ada test yang membutuhkan jaringan.

## 9. Catatan dependensi — OpenZeppelin v5.7.0 DIPAKAI (disetujui pemilik)

Pemilik (Teuku) menyetujui pemakaian OpenZeppelin pada 20 Nov 2026.
Refactor selesai hari yang sama:

- **Sumber:** submodule git `repo/lib/openzeppelin-contracts/`,
  tag `v5.7.0`, rev `cab19933c33c2ad1d4c7a84864a3601dddfd16f3`,
  dikunci oleh `foundry.lock` di root repo. Gitlink submodule tercatat
  di commit (sebelumnya index sempat mencatat rev lama `d98b8f4`;
  diperbaiki saat commit refactor).
- **Yang dipakai:** `ERC20` (BKC), `Ownable` + `ReentrancyGuard`
  (TeamVesting), `Ownable` + `Pausable` + `ReentrancyGuard` +
  `MerkleProof.verifyCalldata` (CommunityClaim), dan
  `IERC20Errors` (hanya di test, untuk selector error OZ).
  Tidak ada impor OZ lain — jangan impor yang tidak dipakai.
- **Cara kerja remapping:** `foundry.toml` di `smart-contracts/vesting/`
  memetakan `@openzeppelin/contracts/` ke
  `../../lib/openzeppelin-contracts/contracts/` (relatif terhadap
  project root Foundry) plus `allow_paths` untuk direktori itu, karena
  solc menolak file di luar project root tanpa izin eksplisit.
- **Clone yang benar:** `git clone --recursive <repo>` (atau
  `git submodule update --init` setelah clone biasa) — tanpa itu
  direktori `lib/openzeppelin-contracts/` kosong dan `forge build` gagal.
- Perilaku kontrak **tetap sama** dengan spesifikasi v0.1: max supply
  1 miliar, tanpa mint pasca-deploy, vesting cliff 90 hari + linear
  270 hari, revocable hanya sebelum cliff, claim Merkle sekali per
  alamat, pausable. Yang berubah: implementasi memakai standar OZ
  (termasuk `transferOwnership` pada owner — lihat §2.3 dan §7 butir 10),
  error memakai error OZ (`OwnableUnauthorizedAccount`,
  `EnforcedPause`, `ERC20InsufficientBalance`, dll.), dan fungsi
  transfer dana dilindungi `nonReentrant`.
- Test memakai interface cheatcode minimal lokal (`test/Vm.sol`) tanpa
  `forge-std` — tidak berubah.

## 10. Yang masih butuh keputusan pemilik (untuk induk)

1. **Alamat beneficiary tim** (parameter constructor `TeamVesting`) —
   alamat multisig/treasury tim yang sesungguhnya. Belum ada.
2. **Alamat owner/admin** untuk kedua kontrak — EOA sementara vs multisig
   vs multisig+timelock. Direkomendasikan multisig.
3. **`start` vesting** — tanggal mainnet launch yang sesungguhnya.
4. **Pool & daftar klaim komunitas** — jumlah BKC pool airdrop final,
   daftar alamat + amount, kriteria eligibility/anti-Sybil, dan siapa
   yang membangun Merkle tree (builder harus cocok §3.1).
5. **Pemetaan `abkc` (Cosmos bank) ↔ BKC ERC-20** — bagaimana token ini
   berhubungan dengan coin native di chain (bridge/mapping/EVM bank
   precompile). Tanpa ini, jangan anggap supply EVM = supply chain.
6. **Opsi dependensi OpenZeppelin** (§9) — **SELESAI, diputuskan pemilik
   20 Nov 2026: pakai OZ.** Refactor selesai, 37/37 test lolos.
7. **Satu beneficiary vs banyak penerima tim** — bila banyak, deploy satu
   kontrak per penerima atau revisi spesifikasi.
8. **Jadwal deploy & audit** — urutan yang diusulkan: review Security
   Auditor AI → deploy Sepolia → uji klaim/vesting dengan data asli →
   audit eksternal → baru pertimbangkan mainnet. Semua butuh persetujuan
   eksplisit Teuku; **tidak ada langkah deploy yang dilakukan di sini**.
