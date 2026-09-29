"""
Критичный сценарий: после подключения и по кнопке «Обновить» таблица
показывает ровно те данные, которые отправил сервис.

Шаги:
  1. Запущен сервис (порт 2001) и приложение.
  2. «Подключиться» -> в таблице 10 сигналов, каждый совпадает с
     отправленным сервисом по ID, имени, значению, качеству и времени.
  3. «Обновить» -> приложение запрашивает новые данные, таблица показывает
     НОВЫЙ снимок (а не старый) и он тоже совпадает с отправленным.
"""

from datetime import datetime, timezone

from conftest import wait_for
from fake_service import SIGNAL_COUNT

VALUE_TOLERANCE = 0.0005     # UI показывает 3 знака после запятой
TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"   # формат колонки «Время» в UI (UTC)
TIME_TOLERANCE_S = 0.001     # UI показывает миллисекунды


def parse_service_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def parse_ui_ts(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT).replace(tzinfo=timezone.utc)


def assert_table_matches(rows, snapshot):
    """Сравнивает таблицу с эталоном по каждому сигналу, собирая все расхождения сразу."""
    # Ровно 10 строк: ни потерянных, ни задублированных сигналов
    assert len(rows) == SIGNAL_COUNT, f"Ожидалось {SIGNAL_COUNT} строк, в таблице {len(rows)}"

    ui_by_id = {r.id: r for r in rows}
    assert len(ui_by_id) == len(rows), f"В таблице есть дубли ID: {[r.id for r in rows]}"

    errors = []
    for sent in snapshot:
        row = ui_by_id.get(str(sent["id"]))
        if row is None:
            errors.append(f"ID {sent['id']}: сигнал отсутствует в таблице")
            continue
        if row.name != sent["name"]:
            errors.append(f"ID {sent['id']}: имя '{row.name}' != '{sent['name']}'")
        # Главная проверка: значение в UI == отправленному (с точностью отображения)
        try:
            if abs(float(row.value) - sent["value"]) > VALUE_TOLERANCE:
                errors.append(f"ID {sent['id']}: значение {row.value} != {sent['value']}")
        except ValueError:
            errors.append(f"ID {sent['id']}: значение не число: '{row.value}'")
        if row.quality != sent["quality"]:
            errors.append(f"ID {sent['id']}: качество '{row.quality}' != '{sent['quality']}'")
        # Время — метка источника, а не время отрисовки
        try:
            delta = abs((parse_ui_ts(row.time) - parse_service_ts(sent["timestamp"])).total_seconds())
            if delta > TIME_TOLERANCE_S:
                errors.append(f"ID {sent['id']}: время '{row.time}' != '{sent['timestamp']}'")
        except ValueError:
            errors.append(f"ID {sent['id']}: неверный формат времени '{row.time}'")

    assert not errors, "Данные в таблице не совпадают с отправленными сервисом:\n" + "\n".join(errors)


def test_table_shows_exact_service_data_after_connect_and_refresh(app, service):
    # Предусловие: структура таблицы соответствует требованиям
    assert app.header() == ["ID", "Имя", "Значение", "Качество", "Время"]

    # --- Шаг 1: подключение ---
    app.click_connect()
    assert wait_for(lambda: service.request_count >= 1), "Приложение не запросило данные после подключения"
    first_snapshot = service.last_snapshot

    # Ждём, пока UI отрисует 10 строк, затем строго сравниваем с эталоном
    rows = app.wait_table(lambda r: len(r) == SIGNAL_COUNT)
    assert_table_matches(rows, first_snapshot)

    # --- Шаг 2: ручное обновление ---
    requests_before = service.request_count
    old_times = {r.time for r in rows}
    app.click_refresh()
    assert wait_for(lambda: service.request_count > requests_before), \
        "По кнопке «Обновить» приложение не отправило запрос в сервис"
    second_snapshot = service.last_snapshot

    # Ждём, пока в таблице сменится время (признак, что отрисован новый снимок)
    rows = app.wait_table(lambda r: len(r) == SIGNAL_COUNT and {x.time for x in r} != old_times)
    # Если таблица осталась со старыми данными — это баг "залипших" значений,
    # assert ниже его поймает: значения/время не совпадут со вторым снимком
    assert_table_matches(rows, second_snapshot)

    # Санити: данные действительно изменились, т.е. тест проверил именно обновление
    assert [s["value"] for s in first_snapshot] != [s["value"] for s in second_snapshot]
