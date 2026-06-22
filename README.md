# 🧬 CodeDNA — AI Kod Şeffaflık Aracı

Her commit'te hangi kodun AI tarafından yazıldığını tespit eden, geliştiricinin o kodu gerçekten anlayıp anlamadığını ölçen ve takım genelinde "anlama borcu" haritası çıkaran CLI aracı.

## Kurulum

```bash
# Geliştirme ortamı için
uv pip install -e .

# veya
pip install codedna
```

## Kullanım

```bash
# Git hook'u kur ve veritabanını oluştur
codedna init

# Tüm repoyu tara
codedna scan

# Son commit skorunu göster
codedna status

# Geçmiş commit skorlarını listele
codedna history

# Hook'u kaldır
codedna uninstall
```

## Nasıl Çalışır?

`codedna scan` komutu her desteklenen dosyayı (`*.py`, `*.js`, `*.ts`, `*.jsx`, `*.tsx`) analiz eder:

| Metrik | Açıklama |
|--------|----------|
| `comment_ratio > 0.3` | AI kodu genelde aşırı yorum yazar → +0.20 |
| `avg_function_length > 50` | AI büyük fonksiyon blokları üretir → +0.15 |
| `single_commit_ratio > 0.7` | Toplu yapıştırma işareti → +0.30 |
| Yüksek karmaşıklık + tek commit | AI imzası → +0.25 |

## Gereksinimler

- Python 3.10+
- Git kurulu olmalı
# test
# test2
