# ADR-0006: Client persistence abstraction

Статус: принято.

Application layer зависит от `LocalPersistence`/repository interfaces. Web-реализация может использовать IndexedDB/Dexie; native — SQLite. I-0 предоставляет интерфейс и безопасный in-memory bootstrap; полноценный offline sync относится к следующему этапу. Platform checks не допускаются в бизнес-слое.
