# I-0 — encryption at rest и ключи

Production PostgreSQL должен размещаться на зашифрованных томах/managed storage. Backup шифруются отдельным ключевым контуром. Секрет подписи JWT, OTP HMAC key и credentials внешних систем должны храниться в Vault/KMS/корпоративном аналоге, а не в git или compose. Владелец и rotation policy назначаются эксплуатацией до production deployment. Для native auth secrets используется Keychain/Keystore через secure-storage adapter. Web refresh token не сохраняется в IndexedDB/localStorage.
