# Security Policy — BLACKCHAIN (DRAFT v0.1)

## Melaporkan kerentanan

Jika Anda menemukan kerentanan keamanan, JANGAN membuka issue publik.
Kirim laporan ke alamat email security resmi yang akan diumumkan bersama
domain resmi proyek. Sertakan: deskripsi, langkah reproduksi, dampak yang
diperkirakan, dan (bila ada) bukti konsep.

## Yang kami lindungi

- Konsensus dan validator (double-sign, liveness, eclipse, long-range).
- Kontrak vesting, claim, dan airdrop.
- Bridge (cross-chain message verification, replay protection, rate limit,
  emergency pause).
- Wallet (enkripsi private key, mnemonic handling).
- Supply chain dependensi.

## Prinsip

- Audit independen wajib sebelum mainnet dan sebelum bridge tanpa batas.
- Tidak ada seed phrase / private key yang pernah diminta atau disimpan
  oleh AI maupun proyek.
- Tidak ada kredensial infrastruktur yang dipublikasikan di repo ini.
