# ChatGPT (Custom GPT) Kurulumu

1. Yeni bir GPT oluştur, **Instructions** alanına
   [genel-sistem-promptu.md](genel-sistem-promptu.md) içeriğini yapıştır.
2. **Knowledge** bölümüne `agents/`, `templates/` ve
   `setup/workspace-template/` altındaki dosyaları yükle.
3. **Code Interpreter** açıksa çalışma alanı `/mnt/data/ihale-analiz-calisma/`
   altında kurulur; oturumlar arası kalıcı olmadığı için oturum sonunda
   hafıza dosyaları kullanıcıya indirilebilir dosya olarak verilir ve
   sonraki oturumda yeniden yüklenmesi istenir.
