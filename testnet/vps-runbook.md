# BLACKCHAIN — Runbook Deploy Seed Node Publik di VPS (Sesi 11)

**Status 2026-11-21 (Sesi 13): PERSIAPAN — paket deploy sudah ditulis dan
diuji sintaksnya, tetapi BELUM DIEKSEKUSI.** IP VPS sudah diketahui
(`103.147.8.20`, diterima 00:14 WIB), tetapi SSH dari VM ini ke VPS
GAGAL di semua port yang dites (22/80/443/2222/22022, dites ulang
00:47–00:54 WIB) — kemungkinan VPS belum menyala atau firewall provider
menutup port 22. Jalur utama (§2, scp oleh Muse) TERBLOKIR sampai
pemilik memeriksa panel VPS. **Jalur alternatif (§2b): pemilik build
binary dari source di VPS sendiri** — source chain kini ada di repo
(`chain/`, sejak Sesi 13) dan script mendukung flag `--allow-local-build`.
Dokumen desain: `docs/21-vps-seed-deployment.md`.

Chain: `blackchain_20261120-1` · EVM chain ID `20261120` (`0x1352900`) ·
denom `abkc` · binary Jalur A `build/blackchaind-sdk54-bkc`
(SDK v0.54.5 + Cosmos EVM v0.7.4, ~199 MB).

## 0. Ringkasan alur (baca dulu sebelum eksekusi)

```
Pemilik kirim IP + username + OS + konfirmasi kunci (§1)
        ↓
Muse transfer binary + genesis + script dari VM ini via scp (§2)
   — ATAU pemilik build binary dari source di VPS (§2b, bila SSH dari VM terblokir)
        ↓
Jalankan vps-deploy.sh DI VPS → seed node hidup, P2P 26656 publik (§3)
        ↓
4 validator lokal dial KELUAR ke seed VPS, satu per satu (§4)
        ↓
Verifikasi seed dari luar + isi seeds.md (§5)
        ↓
Baru setelah semua hijau: umumkan (butuh persetujuan pemilik, docs/20)
```

**Yang TIDAK dilakukan dalam runbook ini:** genesis baru (rantai tetap
yang sudah berjalan, height ~500+); memindahkan kunci validator ke mana
pun; deploy ke Sepolia/mainnet; membuka RPC/EVM ke publik (keputusan
pemilik terpisah, lihat `docs/21` §4).

## 1. Yang harus dikirim pemilik ke Muse (sebelum eksekusi)

| # | Informasi | Contoh format | Status |
|---|---|---|---|
| 1 | IP publik VPS | `203.0.113.10` | ✅ DITERIMA 21 Nov 00:14 WIB: `103.147.8.20` (SSH dari VM ini tetap gagal — lihat status di atas) |
| 2 | Username SSH | `ubuntu` / `root` / nama lain | ⏳ BELUM DITERIMA |
| 3 | OS / distro + versi | `Ubuntu 24.04` | ⏳ BELUM DITERIMA |
| 4 | Konfirmasi kunci publik sudah masuk `authorized_keys` | "sudah" + cara cek | ⏳ BELUM DITERIMA |
| 5 | (Opsional) spesifikasi VPS | vCPU / RAM / disk | ⏳ BELUM DITERIMA (untuk build dari source: RAM min 2 GB, disk kosong min 10 GB) |

Kunci publik Muse (satu-satunya yang boleh dipasang di VPS):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIwyBwm8auOVFGcuLoyNopkrrdOpWGwmDaon74CIDf7Z hatch
```

Di VPS, pemilik (atau siapa pun yang punya akses awal) memasangnya dengan:

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIwyBwm8auOVFGcuLoyNopkrrdOpWGwmDaon74CIDf7Z hatch" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**JANGAN PERNAH** kirim password, private key, seed phrase, atau mnemonic
lewat chat — kunci di atas adalah kunci PUBLIK saja. Bila VPS hanya bisa
diakses dengan password, pemilik yang login pertama kali dan memasang
kunci di atas, atau memberi tahu Muse cara akses alternatif yang aman.

> Placeholder di seluruh dokumen ini: `<IP-PUBLIK-VPS>`,
> `<USERNAME-SSH>`, `<NODE-ID-SEED>`. Semua itu BELUM diketahui dan
> TIDAK BOLEH dikarang — isi setelah §3 selesai dan terverifikasi.

## 2. Transfer file dari VM ini ke VPS (dijalankan Muse dari VM ini)

**Prasyarat:** §1 lengkap + koneksi SSH dari VM ini ke VPS berhasil
(`ssh <USERNAME-SSH>@<IP-PUBLIK-VPS> "echo ok"`).

Binary TIDAK di-build dari GitHub — scaffold chain tidak ada di repo
(`build/` di-gitignore). Yang ditransfer adalah binary Jalur A yang
sudah berjalan di VM ini, beserta genesis testnet final.

```bash
# Dari VM ini (direktori kerja bebas):
scp ~/workspace/blackchain/build/blackchaind-sdk54-bkc \
    <USERNAME-SSH>@<IP-PUBLIK-VPS>:/home/<USERNAME-SSH>/blackchain-deploy/blackchaind

scp ~/workspace/blackchain/repo/testnet/blackchain-testnet-genesis.json \
    <USERNAME-SSH>@<IP-PUBLIK-VPS>:/home/<USERNAME-SSH>/blackchain-deploy/blackchain-testnet-genesis.json

scp ~/workspace/blackchain/repo/testnet/vps-deploy.sh \
    <USERNAME-SSH>@<IP-PUBLIK-VPS>:/home/<USERNAME-SSH>/blackchain-deploy/vps-deploy.sh
```

Catatan:

- Binary ~199 MB — transfer sekali saja; bila gagal di tengah, ulangi
  perintah yang sama (scp menimpa file sebagian).
- `vps-deploy.sh` sendiri memverifikasi sha256 kedua file sebelum
  deploy (binary `37766ab8…b9f06`, genesis `0fbd6b09…52431` — nilai
  lengkap ada di dalam script). Bila sha256 tidak cocok, STOP dan
  transfer ulang — jangan lanjut.
- Bila pemilik memberi VPS dengan user `root` saja, buat dulu user
  non-root di VPS (`adduser blackchain` + `usermod -aG sudo blackchain`)
  dan jalankan semua langkah berikut sebagai user itu. Script deploy
  MENOLAK berjalan sebagai root.

## 2b. Alternatif: build binary dari source DI VPS (bila SSH dari VM terblokir)

Dipakai sejak Sesi 13, ketika SSH dari VM ini ke VPS tidak bisa masuk
(port 22 tidak menjawab) sehingga §2 tidak bisa dijalankan Muse. Source
chain lengkap kini ada di repo (`chain/`, Cosmos SDK v0.54.5 + Cosmos EVM
v0.7.4) — build ulang dari source yang sama TERBUKTI menghasilkan binary
yang jalan (diuji 2026-11-21 di VM ini: build bersih ~30 detik dengan
module cache hangat, binary ~199 MB, `--help` + `version --long` OK).

```bash
# Di VPS, sebagai user non-root dengan sudo tanpa password.
# Syarat: Ubuntu 22.04/24.04 atau Debian 12, RAM min 2 GB (disarankan 4 GB),
# disk kosong min 10 GB, akses internet.
# Langkah lengkap + penjelasan ada di chain/BUILD.md — ringkasnya:
sudo apt update && sudo apt install -y git gcc build-essential curl jq wget
cd ~
wget https://go.dev/dl/go1.27.4.linux-amd64.tar.gz
sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.27.4.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
go version   # harus: go version go1.27.4 linux/amd64
git clone https://github.com/BlackchainLabs/blackchain.git
cd blackchain/chain
mkdir -p ~/tmp-go-build && export TMPDIR=$HOME/tmp-go-build
go build -o blackchaind ./cmd/blackchaind   # unduh module pertama kali; 10-30 menit
./blackchaind --help | head -5

# Siapkan file untuk deploy (§3):
mkdir -p ~/blackchain-deploy
cp blackchaind ~/blackchain-deploy/blackchaind
cd ~/blackchain-deploy
curl -L -o blackchain-testnet-genesis.json https://raw.githubusercontent.com/BlackchainLabs/blackchain/main/testnet/blackchain-testnet-genesis.json
curl -L -o vps-deploy.sh https://raw.githubusercontent.com/BlackchainLabs/blackchain/main/testnet/vps-deploy.sh
chmod +x vps-deploy.sh
```

**PENTING — flag `--allow-local-build`:** binary hasil build lokal di VPS
SELALU beda sha256-nya dari binary hasil build di VM pengembang (metadata
build: path, versi Go, ldflags) — dibuktikan 2026-11-21 (`48088178...` vs
`37766ab8...`). Karena itu deploy dari binary build-sendiri WAJIB memakai
flag itu di §3 (`./vps-deploy.sh <IP> --allow-local-build`): cek sha256
binary dilewati, genesis tetap dicek. Jangan pernah pakai flag ini untuk
binary dari sumber yang tidak kamu build sendiri.

## 3. Menjalankan deploy DI VPS

```bash
# Di VPS, sebagai user non-root:
cd ~/blackchain-deploy
chmod +x vps-deploy.sh

# 1) Cek rencana dulu (tanpa efek samping):
./vps-deploy.sh <IP-PUBLIK-VPS> --dry-run

# 2) Bila dry-run OK, jalankan deploy penuh:
./vps-deploy.sh <IP-PUBLIK-VPS>
#    — bila binary hasil build sendiri di VPS (§2b), tambahkan flag:
#    ./vps-deploy.sh <IP-PUBLIK-VPS> --allow-local-build
```

Yang dilakukan script (detail di `vps-deploy.sh` + `docs/21`):

1. Cek OS + dependensi (`curl`, `jq`, `ufw`, `systemctl`, `python3`).
2. Verifikasi sha256 binary + genesis (cek binary dilewati bila
   `--allow-local-build`, lihat §2b).
3. Instal binary ke `/usr/local/bin/blackchaind`.
4. `blackchaind init blackchain-seed-1 --chain-id blackchain_20261120-1`
   ke `~/.blackchain`, salin genesis, `genesis validate`.
5. Konfigurasi `config.toml`: P2P `0.0.0.0:26656`,
   `external_address <IP-PUBLIK-VPS>:26656`, `seed_mode = true`,
   `persistent_peers` kosong, `addr_book_strict = true`,
   `allow_duplicate_ip = false`; RPC `127.0.0.1:26657`.
   `app.toml`: gRPC `127.0.0.1:9090`, REST API nonaktif.
6. Systemd service `blackchaind-seed` (restart always).
7. UFW: allow `22` + `26656`; deny `26657`, `8545`, `8546`, `9090`, `1317`.
8. Start + verifikasi awal (status, `eth_chainId`, node ID).

**Output yang WAJIB dicatat dari langkah ini:**

```
Node ID seed: <NODE-ID-SEED>
Alamat seed publik: <NODE-ID-SEED>@<IP-PUBLIK-VPS>:26656
```

Bila script gagal di tengah: baca pesan error-nya (script berhenti di
langkah yang gagal — `set -e`), perbaiki penyebabnya, jalankan ulang.
Bila `~/.blackchain` sudah terbuat tetapi deploy gagal sebelum selesai,
hapus home itu (`rm -rf ~/.blackchain`) dan mulai dari `init` lagi —
JANGAN hapus home node yang sudah sinkron penuh.

## 4. Menghubungkan 4 validator lokal ke seed VPS (MANUAL, setelah §3)

> ⚠️ **BACA SEBELUM MENJALANKAN BAGIAN INI.**
>
> - Lakukan HANYA setelah seed VPS terverifikasi hidup (§3 + §5 langkah
>   dari dalam VPS). Seed yang mati tidak berguna sebagai peer.
> - Restart validator **SATU PER SATU** (val1 → tunggu sinkron →
>   val2 → …). Jaringan butuh kuorum **> 2/3** — dengan 4 validator,
>   yang boleh mati bersamaan MAKSIMAL 1 node. Dua node mati bersamaan
>   = chain halt (pelajaran F33, `docs/17`).
> - Perintah di bawah ini DIJALANKAN DI VM INI, bukan di VPS.
> - JANGAN ubah apa pun selain `persistent_peers`: peer lokal
>   (127.0.0.1) TETAP dipertahankan — seed VPS DITAMBAHKAN di akhir
>   daftar, bukan menggantikan peer lokal. Bila seed VPS mati nanti,
>   keempat validator tetap terhubung satu sama lain.
> - JANGAN pindahkan file kunci apa pun (`priv_validator_key.json`,
>   `node_key.json`, keyring) keluar VM ini.

### 4.1 Tambahkan seed ke `persistent_peers` tiap validator

Ganti placeholder `<NODE-ID-SEED>` dan `<IP-PUBLIK-VPS>` dengan nilai
dari §3. Perintah ini mengedit HANYA baris `persistent_peers` di section
`[p2p]` (parser per-baris; tidak menyentuh kunci lain):

```bash
cd ~/workspace/blackchain

SEED="<NODE-ID-SEED>@<IP-PUBLIK-VPS>:26656"

for i in 1 2 3 4; do
  python3 - testnet-data/val$i/config/config.toml "$SEED" <<'PYEOF'
import sys
path, seed = sys.argv[1], sys.argv[2]
lines = open(path).read().splitlines(keepends=True)
out, section, done = [], None, False
for line in lines:
    s = line.strip()
    if s.startswith('[') and s.endswith(']'):
        section = s[1:-1].strip()
        out.append(line)
        continue
    if section == 'p2p' and s.startswith('persistent_peers') and '=' in line and not done:
        cur = line.split('=', 1)[1].strip().strip('"')
        peers = [p for p in cur.split(',') if p]
        if seed not in peers:
            peers.append(seed)
        out.append('persistent_peers = "' + ','.join(peers) + '"\n')
        done = True
        continue
    out.append(line)
if not done:
    raise SystemExit(f'persistent_peers tidak ditemukan di {path}')
open(path, 'w').write(''.join(out))
print(f'{path}: seed ditambahkan')
PYEOF
done

# Verifikasi hasil edit (harus 4 baris, tiap baris = 3 peer lokal + seed):
grep -h '^persistent_peers' testnet-data/val{1,2,3,4}/config/config.toml
```

Nilai `persistent_peers` ASLI (sebelum edit — simpan untuk rollback §6):

| Node | persistent_peers asli |
|---|---|
| val1 | `1cc0f94349707b4f3a9ac8b69e3c40fec9010f32@127.0.0.1:26786,7e7320fa5271e2c9cec93ecb0dc74d495b1fc80e@127.0.0.1:26796,fcae4c9ecb0a8635c7b2b1352d1ab8579e9bca84@127.0.0.1:26806` |
| val2 | `9088193266bf7fe1addf21ea42dfa8c5b3ff97a2@127.0.0.1:26776,7e7320fa5271e2c9cec93ecb0dc74d495b1fc80e@127.0.0.1:26796,fcae4c9ecb0a8635c7b2b1352d1ab8579e9bca84@127.0.0.1:26806` |
| val3 | `9088193266bf7fe1addf21ea42dfa8c5b3ff97a2@127.0.0.1:26776,1cc0f94349707b4f3a9ac8b69e3c40fec9010f32@127.0.0.1:26786,fcae4c9ecb0a8635c7b2b1352d1ab8579e9bca84@127.0.0.1:26806` |
| val4 | `9088193266bf7fe1addf21ea42dfa8c5b3ff97a2@127.0.0.1:26776,1cc0f94349707b4f3a9ac8b69e3c40fec9010f32@127.0.0.1:26786,7e7320fa5271e2c9cec93ecb0dc74d495b1fc80e@127.0.0.1:26796` |

### 4.2 Restart validator satu per satu

Perintah start persis seperti saat rehearsal (`docs/17` + proses yang
sedang berjalan di VM ini — JANGAN ubah flag). Jalankan dari
`~/workspace/blackchain`. **Satu node selesai → verifikasi → baru lanjut
ke node berikutnya.**

**val1** (PID lama 12799, RPC 26777, P2P 26776, EVM 8655):

```bash
kill 12799
sleep 5
ps -p 12799 || echo "val1 mati"
nohup ./build/blackchaind-sdk54-bkc start --home /home/hatch/workspace/blackchain/testnet-data/val1 \
  --minimum-gas-prices 0abkc --log_level *:info \
  --rpc.laddr tcp://127.0.0.1:26777 --p2p.laddr tcp://127.0.0.1:26776 \
  --grpc.address 127.0.0.1:9202 --rpc.pprof_laddr 127.0.0.1:6171 \
  --json-rpc.enable=true --json-rpc.address 127.0.0.1:8655 \
  --json-rpc.ws-address 127.0.0.1:8656 \
  >> testnet-data/val1.log 2>&1 < /dev/null &
sleep 30
curl -s http://127.0.0.1:26777/status | python3 -c "import json,sys; d=json.load(sys.stdin)['result']; print('val1 height:', d['sync_info']['latest_block_height'], 'catching_up:', d['sync_info']['catching_up'])"
curl -s http://127.0.0.1:26777/net_info | python3 -c "import json,sys; print('val1 peers:', json.load(sys.stdin)['result']['n_peers'])"
```

**val2** (PID lama 12800, RPC 26787, P2P 26786, EVM 8665) — sama, ganti
angka: home `val2`, RPC `26787`, P2P `26786`, grpc `9203`, pprof `6172`,
json `8665`, ws `8666`, log `testnet-data/val2.log`.

**val3** (PID lama 12801, RPC 26797, P2P 26796, EVM 8675): home `val3`,
RPC `26797`, P2P `26796`, grpc `9204`, pprof `6173`, json `8675`,
ws `8676`, log `testnet-data/val3.log`.

**val4** (PID lama 12976, RPC 26807, P2P 26806, EVM 8685): home `val4`,
RPC `26807`, P2P `26806`, grpc `9205`, pprof `6174`, json `8685`,
ws `8686`, log `testnet-data/val4.log`.

> Perintah start lengkap tiap node ada di `docs/17` §1 / skrip
> `repo/scripts/setup-testnet-4val.sh` baris 189. PID di atas adalah PID
> yang tercatat 2026-11-21 00:01 WIB — **cek ulang dengan
> `ps aux | grep blackchaind` sebelum `kill`**, karena PID berubah bila
> node pernah di-restart. Jangan `kill` berdasarkan tebakan, dan jangan
> pernah `pkill blackchaind` (pernah membunuh devnet lain — lihat
> catatan Sesi 2).

Kriteria lanjut ke node berikutnya: height node yang baru di-restart
**naik dan sama** dengan ketiga node lain (±1 blok), `catching_up: false`,
dan `n_peers` ≥ 3 (3 peer lokal; setelah semua terhubung, peer ke seed
VPS ikut terhitung sehingga total bisa 4).

## 5. Verifikasi seed publik

### 5.1 Dari DALAM VPS (langsung setelah §3)

```bash
sudo systemctl status blackchaind-seed --no-pager | head -20
curl -s http://127.0.0.1:26657/status | jq '{chain_id: .result.node_info.network, height: .result.sync_info.latest_block_height, catching_up: .result.sync_info.catching_up}'
curl -s http://127.0.0.1:26657/net_info | jq '{n_peers: .result.n_peers, peers: [.result.peers[].node_info.id]}'
curl -s -X POST http://127.0.0.1:8545 -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'
# Harus mengembalikan 0x1352900 (= 20261120).
```

Kriteria lolos: service `active (running)`; `chain_id`
`blackchain_20261120-1`; height SAMA dengan 4 validator lokal (±2 blok,
karena seed butuh mengejar dari genesis — tunggu sampai `catching_up:
false`); `eth_chainId` = `0x1352900`.

### 5.2 Dari LUAR (setelah §4 — bukti seed benar-benar bisa di-dial)

RPC VPS sengaja TERTUTUP, jadi verifikasi dari luar TIDAK memakai curl
ke port 26657. Buktinya adalah node baru bisa sync lewat seed:

```bash
# Di mesin mana pun yang punya binary blackchaind (mis. VM ini, home baru):
blackchaind init verifikasi-seed --chain-id blackchain_20261120-1 --home /tmp/verifikasi-seed
cp ~/workspace/blackchain/repo/testnet/blackchain-testnet-genesis.json /tmp/verifikasi-seed/config/genesis.json
blackchaind start --home /tmp/verifikasi-seed \
  --minimum-gas-prices 0abkc \
  --p2p.seeds "<NODE-ID-SEED>@<IP-PUBLIK-VPS>:26656" \
  --rpc.laddr tcp://127.0.0.1:26999 --p2p.laddr tcp://127.0.0.1:26998 \
  --json-rpc.enable=true --json-rpc.address 127.0.0.1:8699 &
sleep 60
curl -s http://127.0.0.1:26999/status | jq '.result.sync_info'
# Harus menunjukkan height naik menuju height jaringan, catching_up true
# lalu false. Bila height mentok di 1 dan n_peers 0 → seed tidak bisa
# di-dial dari luar (cek ufw + provider firewall VPS + external_address).
```

Setelah verifikasi selesai, matikan node verifikasi itu
(`kill <PID>`; home `/tmp/verifikasi-seed` boleh dihapus — tidak ada
kunci penting di dalamnya).

### 5.3 Setelah semua hijau

1. Isi alamat seed (`<NODE-ID-SEED>@<IP-PUBLIK-VPS>:26656`) ke
   `repo/testnet/seeds.md` bagian "Seed publik (VPS)" — ganti
   placeholder, sertakan tanggal + height saat verifikasi.
2. Perbarui `docs/14` (checklist) dan mission log.
3. Push ke GitHub via snapshot push (seperti sesi-sesi sebelumnya).
4. Pengumuman resmi (`docs/20`) HANYA setelah persetujuan eksplisit
   pemilik — jangan posting sebelum itu.

## 6. Rollback (bila seed VPS bermasalah)

Rantai lokal TIDAK tergantung pada seed VPS — keempat validator tetap
saling terhubung lewat peer 127.0.0.1. Rollback = putuskan sambungan ke
seed, rantai jalan terus.

```bash
# 1) Matikan seed di VPS:
ssh <USERNAME-SSH>@<IP-PUBLIK-VPS> "sudo systemctl stop blackchaind-seed; sudo systemctl disable blackchaind-seed"

# 2) Di VM ini, kembalikan persistent_peers tiap validator ke nilai ASLI
#    (tabel §4.1) — hapus entri seed dari daftar, lalu restart SATU PER
#    SATU seperti §4.2 (kuorum 3/4 harus dijaga).
#    Cara tercepat: edit manual baris persistent_peers di
#    testnet-data/val{1,2,3,4}/config/config.toml, atau jalankan lagi
#    skrip python §4.1 dengan SEED="" — JANGAN; skrip itu hanya menambah.
#    Edit manual dan verifikasi dengan grep sebelum restart.

# 3) Verifikasi: keempat node height sama, catching_up false,
#    n_peers = 3 (hanya peer lokal).
```

Bila yang rusak hanya VPS-nya (bukan konfigurasinya), seed bisa
dibangun ulang dari §2–§3 dengan home baru — node ID akan berubah,
sehingga `seeds.md` + `persistent_peers` lokal harus diperbarui dengan
node ID baru. Genesis TETAP sama.
