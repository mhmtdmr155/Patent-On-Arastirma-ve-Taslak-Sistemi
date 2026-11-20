# PROJE ÇALIŞMA KURALLARI VE SÜRÜM KONTROL PROTOKOLÜ (WORKFLOW RULES)

Bu belge, **Yapay Zekâ Destekli Patent Ön Araştırma ve Patent Taslağı Hazırlama Sistemi** projesinde Antigravity/Gemini agentic asistanının uymakla yükümlü olduğu kalıcı çalışma kurallarını, denetim ilkelerini ve Git sürüm kontrol protokolünü tanımlar. `GEMINI.md` dosyası ile tam senkronize ve eşdeğerdir.

---

## KALICI PROJE KURALLARI

### KALICI KURAL 1: Proje Mülkiyeti ve Bireysel Kapsam
*   **Proje Sahibi:** Mehmet Demir (Kahramanmaraş Sütçü İmam Üniversitesi, Bilgisayar Mühendisliği Bölümü).
*   **Proje Niteliği:** Bu çalışma tek kişilik bir lisans bitirme projesidir.
*   **Kural:** Başka ders projelerinin veya harici çalışmaların ekip üyeleri bu projeye ve belgelerine kesinlikle dahil edilemez.

### KALICI KURAL 2: ChatGPT Koordinasyonu ve Görev Ayrımı
*   **Planlama ve Kritik Denetim:** Bağımsız olarak ChatGPT tarafından yürütülür.
*   **Kod Geliştirme ve Yerel Yürütme:** Google Antigravity / Gemini modeli tarafından gerçekleştirilir.
*   **Çalışma İlkesi:** Antigravity, ChatGPT'nin denetim raporlarındaki bulguları bağımsız olarak kaynak kodda ve veri tabanında doğrular, bilimsel kanıtlara dayalı çözümler üretir.

### KALICI KURAL 3: Görev Takip Kodu ve Kanıtlı Raporlama
*   Tüm görevler resmi **PAT-xxxx** (ör. PAT-0104, PAT-0450, PAT-GIT-0001) kodlarıyla takip edilir.
*   Her görev sonunda varsayımlardan uzak, dosya yolları, test çıktıları, ölçüm metrikleri ve SHA-256 özetleriyle desteklenen ayrıntılı ve kanıtlı teknik rapor hazırlanır.
*   Kanıtlanamayan hiçbir işe "PASS" veya "TAMAMLANDI" denilemez; hata varsa açıkça itiraf edilir.

### KALICI KURAL 4: ChatGPT Teslim Dosyaları Başlığı Zorunluluğu
Her teknik raporun en sonunda MUTLAKA ve İSTİSNASIZ aşağıdaki başlık bulunmalıdır:

```text
CHATGPT'YE TESLİM EDİLECEK DOSYALAR:
[Varsa: Dosya adı, tam yerel dosya yolu, görevi, SHA-256 özeti]
[Yoksa: YOK]
```

### KALICI KURAL 5: Gün İçi Geliştirme ve Git İzolasyonu
*   Normal geliştirme görevlerinin (promptların) sonunda GitHub'a commit veya push YAPILMAZ.
*   Bütün günün değişiklikleri yerel Git çalışma alanında (working directory / local branch) tutulur.
*   Gereksiz commit kalabalığı ve ara durumların GitHub'a sızması önlenir.

### KALICI KURAL 6: Gün Sonu GitHub Gönderim Tetikleyicisi
Kullanıcı aşağıdaki ifadelerden herhangi birini kullandığında:
*   *"Tamam bugünlük bu kadar"*
*   *"Bugünlük yeter"*
*   *"Bugün burada bitirelim"*
*   *"Burada bırakalım"*
*   *"Bugünlük bu kadar, kapatıyoruz"*

Bu ifade, açık ve yetkili bir **GÜN SONU GITHUB GÖNDERİM TALİMATI**dır.
Bu durumda kullanıcıdan tekrar onay istemeden Kalıcı Kural 7'deki 13 adımlı güvenlik iş akışı doğrudan başlatılır.

### KALICI KURAL 7: Gün Sonu Güvenli GitHub Prosedürü (13 Adım)
Gün sonu talimatı alındığında aşağıdaki sıra kesinlikle takip edilir:
1.  **Tüm Günün Değişikliklerini İncele:** `git status` ve `git diff` ile gün boyunca nelerin değiştiğini belirle.
2.  **Gereksiz/Yanlış Dosyaları Ayıkla:** Geçici `.tmp`, `.bak`, `.log` veya deneme dosyalarını temizle.
3.  **.gitignore Kontrolü:** `.gitignore` kurallarının hassas klasörleri koruduğunu doğrula.
4.  **Gizli Veri ve Anahtar Taraması:** API anahtarları, şifreler, token'lar, `.env`, kişisel buluş metinleri ve insan etiketleme CSV'lerinin depoya girmediğini doğrula.
5.  **Testleri Çalıştır:** Proje test paketini (`pytest -v`) çalıştır; kırılan regresyon varsa push'u durdur ve düzelt.
6.  **Gerçek Git Diff İncelemesi:** `git diff` çıktısını gözden geçirerek beklenmeyen satır değişikliklerini engelle.
7.  **Uygun Dosyaları Stage Et:** Yalnızca depoya girmesi onaylanan dosyaları `git add` ile stage et.
8.  **Anlamlı Commit Oluştur:** Conventional Commits standardında (ör. `feat:`, `fix:`, `docs:`, `chore:`) açıklayıcı mesaj yaz.
9.  **Remote Adresini Doğrula:** `git remote -v` ile hedefin `mhmtdmr155/Patent-On-Arastirma-ve-Taslak-Sistemi` olduğunu doğrula.
10. **Repository Gizliliğini Doğrula:** Repository'nin `PRIVATE` olduğunu `gh repo view` ile kontrol et.
11. **Main Dalına Push Yap:** `git push origin main` komutunu force kullanmadan çalıştır.
12. **GitHub Commit SHA Doğrulaması:** GitHub API veya `gh` CLI üzerinden uzak commit SHA'sını oku.
13. **Raporlama:** `git status` ve yerel/uzak commit eşleşmesini kullanıcıya ve rapora kanıtla sun.

### KALICI KURAL 8: Kesinlikle Yasaklı İşlemler
*   `git push --force` veya `git push -f` KULLANILAMAZ.
*   `git reset --hard` KULLANILAMAZ.
*   `git clean -fd` KULLANILAMAZ.
*   Gizli anahtar (`.env`, token, şifre) veya insan etiketi (`labeling_queue.csv`) stage edilemez.
*   Hedef dışındaki başka bir repository'ye push yapılamaz.
*   Repository `PUBLIC` yapılamaz; daima `PRIVATE` kalmalıdır.
*   Kullanıcının yerel veri dosyaları silinemez.
*   Başarısız bir push işlemi asla "başarılı" olarak raporlanamaz.
