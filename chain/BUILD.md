# BLACKCHAIN — Build `blackchaind` dari source

Binary node testnet BLACKCHAIN: **Cosmos SDK v0.54.5 + Cosmos EVM v0.7.4**,
dibangun dari source di direktori ini (`chain/`). Source ini adalah scaffold
Jalur A yang sama dengan yang dipakai devnet dan rehearsal 4-validator di VM
pengembang — sudah terbukti build dan jalan (Sesi 3, 4, 8, 12).

## Syarat VPS

- Ubuntu 22.04 / 24.04 atau Debian 12 (64-bit x86_64)
- RAM minimal **2 GB** (disarankan 4 GB — proses link binary ~200 MB butuh memori)
- Disk kosong minimal **10 GB** (module Go ~2 GB + hasil build)
- Akses internet (unduh Go + module Go)
- User non-root dengan `sudo` tanpa password (script deploy menolak `root`)

## Perintah (jalankan di VPS)

```bash
# 1. Dependensi
sudo apt update && sudo apt install -y git gcc build-essential curl jq wget

# 2. Go 1.27.4 (go.mod meminta go 1.26.7; Go 1.27.4 memenuhinya)
cd ~
wget https://go.dev/dl/go1.27.4.linux-amd64.tar.gz
sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.27.4.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
go version   # harus: go version go1.27.4 linux/amd64

# 3. Clone repo + build (unduh module pertama kali; 10-30 menit di VPS kecil)
git clone https://github.com/BlackchainLabs/blackchain.git
cd blackchain/chain
mkdir -p ~/tmp-go-build && export TMPDIR=$HOME/tmp-go-build
# PENTING: /tmp di sebagian VPS terlalu kecil untuk link binary 200 MB —
# TMPDIR di atas memindahkan file sementara build ke $HOME.
go build -o blackchaind ./cmd/blackchaind
./blackchaind version --long | head -3
./blackchaind --help | head -5
```

Build yang sukses menghasilkan `blackchaind` ~199 MB dan perintah di atas
tidak error. Tidak perlu `make`: Makefile memakai variabel git yang tidak
diperlukan untuk binary ini.

## Lanjut deploy seed node

```bash
mkdir -p ~/blackchain-deploy
cp blackchaind ~/blackchain-deploy/blackchaind
cd ~/blackchain-deploy
curl -L -o blackchain-testnet-genesis.json https://raw.githubusercontent.com/BlackchainLabs/blackchain/main/testnet/blackchain-testnet-genesis.json
curl -L -o vps-deploy.sh https://raw.githubusercontent.com/BlackchainLabs/blackchain/main/testnet/vps-deploy.sh
chmod +x vps-deploy.sh
./vps-deploy.sh 103.147.8.20 --allow-local-build
```

> **Catatan sha256:** binary hasil build lokal di VPS TIDAK akan sama
> sha256-nya dengan binary hasil build di VM pengembang (perbedaan metadata
> build: path, versi Go, ldflags). Dibuktikan 2026-11-21: build ulang dari
> source yang sama menghasilkan sha256 `48088178...` vs `37766ab8...`.
> Karena itu flag `--allow-local-build` WAJIB dipakai — flag ini melewati
> cek sha256 binary, tapi genesis tetap dicek sha256-nya. Jangan pernah
> pakai flag ini untuk binary dari sumber yang tidak kamu build sendiri.

Setelah deploy selesai, lanjutkan ke `testnet/vps-runbook.md` §3–§5
(verifikasi seed dari luar + sambungkan 4 validator lokal sebagai peer).
