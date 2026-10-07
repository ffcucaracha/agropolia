# Агрополия

Production-проект «Агрополия». Источник требований — ФТЗ и принятые архитектурные поправки в `docs/`.

Документация нулевой итерации: `docs/i-0/`.

## Разворачивание backend/frontend, требования к серверу и сборка APK

### 1. Локальная среда I-0

Для локальной разработки используется Docker Compose.

Требуется:

- Git;
- Docker Engine;
- Docker Compose v2 (`docker compose`);
- свободные порты `5173`, `8000`, `5432`, `6379`, `4222`, `8222`.

Запуск:

```bash
cp .env.example .env
docker compose up -d --build --wait
docker compose run --rm backend-api alembic upgrade head
```

После запуска:

- frontend: http://localhost:5173
- backend API: http://localhost:8000
- OpenAPI: http://localhost:8000/docs
- NATS monitoring: http://localhost:8222

Проверка состояния backend:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

Development OTP задаётся переменной `AGROPOLIA_DEV_OTP_CODE`. Возврат OTP в API разрешён только для `development/test`; production-конфигурация должна использовать реальный SMS provider.

Остановка:

```bash
docker compose down
```

Полное удаление локальных volumes:

```bash
docker compose down -v
```

### 2. Backend без frontend

Инфраструктура и backend:

```bash
cp .env.example .env
docker compose up -d --build --wait postgres redis nats backend-api backend-worker
docker compose run --rm backend-api alembic upgrade head
```

Критичные переменные окружения:

- `AGROPOLIA_DATABASE_URL`;
- `AGROPOLIA_REDIS_URL`;
- `AGROPOLIA_NATS_URL`;
- `AGROPOLIA_JWT_SECRET`;
- `AGROPOLIA_OTP_SECRET`;
- `AGROPOLIA_WEB_ORIGIN`;
- server-side Android/iOS version policy variables.

Production secrets нельзя брать из `.env.example` или хранить в Git. Для production они должны приходить из Vault/KMS/корпоративного secret storage.

### 3. Frontend

Для standalone frontend development нужен Node.js 22+.

```bash
cd apps/client
npm install
npm run typecheck
npm test -- --run
npm run dev
```

Production web build:

```bash
cd apps/client
VITE_API_BASE_URL=https://api.example.ru/api/v1 npm run build
```

Результат находится в:

```text
apps/client/dist/
```

Каталог `dist/` должен обслуживаться обычным HTTPS static server/reverse proxy (например, nginx). Текущий `client` service в `compose.yaml` запускает Vite dev server и предназначен для разработки/I-0 проверки, а не для production serving.

### 4. Требования к серверу

Формальный production capacity sizing в ФТЗ пока не определён. Ниже — инженерный минимум для I-0/dev/stage deployment, а не SLA production.

Минимально для одного I-0 стенда:

- Linux x86_64 или arm64;
- 2 vCPU;
- 4 GB RAM;
- 20 GB свободного SSD;
- Docker Engine + Docker Compose v2;
- исходящий доступ к container registries при первой сборке/обновлении.

Рекомендуемо для комфортного dev/stage:

- 4 vCPU;
- 8 GB RAM;
- 40+ GB SSD.

В production не следует публиковать PostgreSQL, Redis и NATS наружу. Снаружи должны быть доступны только HTTPS frontend/API через reverse proxy/load balancer. Текущие port mappings PostgreSQL/Redis/NATS в `compose.yaml` являются dev-конфигурацией.

Перед production deployment отдельно требуются:

- TLS termination;
- production secret management;
- encrypted storage/volumes;
- backup/PITR для PostgreSQL;
- firewall/network ACL;
- monitoring/alerts;
- production SMS provider;
- production sizing и нагрузочное тестирование.

### 5. Сборка Android APK

Проект использует Capacitor 8.

Для Android-сборки нужны:

- Node.js 22+;
- Android Studio 2025.2.1 или новее;
- Android SDK;
- Android SDK Platform для целевого API; Capacitor 8 использует target SDK 36;
- JDK отдельно обычно не требуется: подходящий JDK устанавливается Android Studio.

Первичная генерация Android native project выполняется один раз:

```bash
cd apps/client
npm install
npm run build
npx cap add android
npx cap sync android
```

После появления каталога `apps/client/android/` его следует хранить в репозитории, если команда принимает managed-native-project подход. Сейчас он исключён из Git и поэтому для device spike генерируется локально.

Перед каждой новой native-сборкой после изменения web-кода:

```bash
cd apps/client
npm run build
npx cap sync android
```

Открыть Android Studio:

```bash
npx cap open android
```

Debug APK из командной строки:

```bash
cd apps/client/android
./gradlew assembleDebug
```

Результат:

```text
apps/client/android/app/build/outputs/apk/debug/app-debug.apk
```

Для Windows:

```powershell
cd apps/client/android
.\gradlew.bat assembleDebug
```

Для установки на подключённое Android-устройство:

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Для release APK/AAB нужен signing key и release signing configuration. Приватный keystore и его пароли не должны попадать в Git. До появления release pipeline безопаснее создавать signed release через Android Studio: **Build -> Generate Signed App Bundle or APK**.

### 6. Backend URL для APK

`VITE_API_BASE_URL=http://localhost:8000/api/v1` годится для browser development, но не для APK на физическом телефоне: `localhost` внутри телефона указывает на сам телефон.

Перед `npm run build` нужно указать backend, доступный с устройства, предпочтительно HTTPS:

```bash
cd apps/client
VITE_API_BASE_URL=https://<test-api-host>/api/v1 npm run build
npx cap sync android
```

Для device spike удобнее всего поднять отдельный test/stage backend с HTTPS и использовать его URL. Это одновременно позволяет корректно проверить CORS, refresh-cookie/native-token path, reconnect и сетевые сценарии.
