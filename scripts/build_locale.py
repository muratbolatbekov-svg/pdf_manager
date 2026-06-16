#!/usr/bin/env python3
"""Build Django locale .po/.mo files without GNU gettext CLI."""
from __future__ import annotations

import re
from pathlib import Path

import polib

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ui_strings import EXTRA_TRANSLATIONS

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = BASE_DIR / 'locale'

SKIP_PARTS = {'.venv', 'venv', 'staticfiles', 'locale', '__pycache__', '.git'}

# Kazakh (kk) and English (en) translations keyed by Russian msgid.
TRANSLATIONS: dict[str, dict[str, str]] = {
    'Дашборд': {'kk': 'Басты бет', 'en': 'Dashboard'},
    'Документы': {'kk': 'Құжаттар', 'en': 'Documents'},
    'Категории': {'kk': 'Санаттар', 'en': 'Categories'},
    'Добавить документ': {'kk': 'Құжат қосу', 'en': 'Add document'},
    'Журнал изменений': {'kk': 'Өзгерістер журналы', 'en': 'Audit log'},
    'Настройки': {'kk': 'Баптаулар', 'en': 'Settings'},
    'Уведомления': {'kk': 'Хабарландырулар', 'en': 'Notifications'},
    'Пользователи': {'kk': 'Пайдаланушылар', 'en': 'Users'},
    'Выйти': {'kk': 'Шығу', 'en': 'Log out'},
    'Войти': {'kk': 'Кіру', 'en': 'Log in'},
    'Меню': {'kk': 'Мәзір', 'en': 'Menu'},
    'Язык': {'kk': 'Тіл', 'en': 'Language'},
    'Активный': {'kk': 'Белсенді', 'en': 'Active'},
    'В архиве': {'kk': 'Мұрағатта', 'en': 'Archived'},
    'Черновик': {'kk': 'Жоба', 'en': 'Draft'},
    'Читатель': {'kk': 'Оқырман', 'en': 'Viewer'},
    'Менеджер': {'kk': 'Менеджер', 'en': 'Manager'},
    'Администратор': {'kk': 'Әкімші', 'en': 'Administrator'},
    'Создание': {'kk': 'Жасалу', 'en': 'Created'},
    'Изменение': {'kk': 'Өзгерту', 'en': 'Updated'},
    'Удаление': {'kk': 'Жою', 'en': 'Deleted'},
    'Название': {'kk': 'Атауы', 'en': 'Title'},
    'Описание': {'kk': 'Сипаттама', 'en': 'Description'},
    'Категория': {'kk': 'Санат', 'en': 'Category'},
    'PDF файл': {'kk': 'PDF файлы', 'en': 'PDF file'},
    'Сумма договора': {'kk': 'Келісім сомасы', 'en': 'Contract amount'},
    'С НДС': {'kk': 'ҚҚС-пен', 'en': 'With VAT'},
    'Да': {'kk': 'Иә', 'en': 'Yes'},
    'Нет': {'kk': 'Жоқ', 'en': 'No'},
    'Подписант': {'kk': 'Қол қоюшы', 'en': 'Signatory'},
    'Автор': {'kk': 'Автор', 'en': 'Author'},
    'Теги': {'kk': 'Тегтер', 'en': 'Tags'},
    'Статус': {'kk': 'Мәртебе', 'en': 'Status'},
    'Дата начала': {'kk': 'Басталу күні', 'en': 'Start date'},
    'Дата окончания': {'kk': 'Аяқталу күні', 'en': 'End date'},
    'Сохранить': {'kk': 'Сақтау', 'en': 'Save'},
    'Отмена': {'kk': 'Болдырмау', 'en': 'Cancel'},
    'Добавить': {'kk': 'Қосу', 'en': 'Add'},
    'Редактировать': {'kk': 'Өңдеу', 'en': 'Edit'},
    'Удалить': {'kk': 'Жою', 'en': 'Delete'},
    'Назад': {'kk': 'Артқа', 'en': 'Back'},
    'Скачать': {'kk': 'Жүктеу', 'en': 'Download'},
    'Открыть': {'kk': 'Ашу', 'en': 'Open'},
    'Поиск': {'kk': 'Іздеу', 'en': 'Search'},
    'Применить': {'kk': 'Қолдану', 'en': 'Apply'},
    'Сбросить': {'kk': 'Тазалау', 'en': 'Reset'},
    'Сбросить всё': {'kk': 'Барлығын тазалау', 'en': 'Reset all'},
    'Фильтры': {'kk': 'Сүзгілер', 'en': 'Filters'},
    'Фильтры:': {'kk': 'Сүзгілер:', 'en': 'Filters:'},
    'Выбрать': {'kk': 'Таңдау', 'en': 'Select'},
    'Экспорт → Excel': {'kk': 'Excel-ге экспорт', 'en': 'Export → Excel'},
    'Всего документов': {'kk': 'Барлық құжаттар', 'en': 'Total documents'},
    'Активных': {'kk': 'Белсенді', 'en': 'Active'},
    'Черновиков': {'kk': 'Жобалар', 'en': 'Drafts'},
    'Аналитика': {'kk': 'Аналитика', 'en': 'Analytics'},
    'Последние документы': {'kk': 'Соңғы құжаттар', 'en': 'Recent documents'},
    'Дата': {'kk': 'Күні', 'en': 'Date'},
    'Сумма': {'kk': 'Сумма', 'en': 'Amount'},
    'Срок': {'kk': 'Мерзім', 'en': 'Deadline'},
    'Документ': {'kk': 'Құжат', 'en': 'Document'},
    'Файл': {'kk': 'Файл', 'en': 'File'},
    'нет': {'kk': 'жоқ', 'en': 'none'},
    'Комментарии': {'kk': 'Пікірлер', 'en': 'Comments'},
    'Версии': {'kk': 'Нұсқалар', 'en': 'Versions'},
    'Отправить': {'kk': 'Жіберу', 'en': 'Send'},
    'текущая': {'kk': 'ағымдағы', 'en': 'current'},
    'система': {'kk': 'жүйе', 'en': 'system'},
    'сегодня': {'kk': 'бүгін', 'en': 'today'},
    'вчера': {'kk': 'кеше', 'en': 'yesterday'},
    'Без категории': {'kk': 'Санатсыз', 'en': 'Uncategorized'},
    'Текущий месяц': {'kk': 'Ағымдағы ай', 'en': 'Current month'},
    'Прошлый месяц': {'kk': 'Өткен ай', 'en': 'Previous month'},
    'Текущий квартал': {'kk': 'Ағымдағы тоқсан', 'en': 'Current quarter'},
    'Прошлый квартал': {'kk': 'Өткен тоқсан', 'en': 'Previous quarter'},
    'Текущий год': {'kk': 'Ағымдағы жыл', 'en': 'Current year'},
    'Янв': {'kk': 'Қаң', 'en': 'Jan'},
    'Фев': {'kk': 'Ақп', 'en': 'Feb'},
    'Мар': {'kk': 'Нау', 'en': 'Mar'},
    'Апр': {'kk': 'Сәу', 'en': 'Apr'},
    'Май': {'kk': 'Мам', 'en': 'May'},
    'Июн': {'kk': 'Мау', 'en': 'Jun'},
    'Июл': {'kk': 'Шіл', 'en': 'Jul'},
    'Авг': {'kk': 'Там', 'en': 'Aug'},
    'Сен': {'kk': 'Қыр', 'en': 'Sep'},
    'Окт': {'kk': 'Қаз', 'en': 'Oct'},
    'Ноя': {'kk': 'Қар', 'en': 'Nov'},
    'Дек': {'kk': 'Жел', 'en': 'Dec'},
    'Доступ запрещён': {'kk': 'Қол жеткізу тыйым салынған', 'en': 'Access denied'},
    'На главную': {'kk': 'Басты бетке', 'en': 'Home'},
    'Недостаточно прав для этого действия.': {
        'kk': 'Бұл әрекет үшін құқық жеткіліксіз.',
        'en': 'You do not have permission for this action.',
    },
    'Документ успешно добавлен!': {'kk': 'Құжат сәтті қосылды!', 'en': 'Document added successfully!'},
    'Документ обновлён!': {'kk': 'Құжат жаңартылды!', 'en': 'Document updated!'},
    'Документ удалён!': {'kk': 'Құжат жойылды!', 'en': 'Document deleted!'},
    'Добавить документ': {'kk': 'Құжат қосу', 'en': 'Add document'},
    'Редактировать': {'kk': 'Өңдеу', 'en': 'Edit'},
    'Обзор системы управления документами': {
        'kk': 'Құжаттарды басқару жүйесінің шолуы',
        'en': 'Document management system overview',
    },
    'Управление договорами и файлами': {
        'kk': 'Келісімдер мен файлдарды басқару',
        'en': 'Manage contracts and files',
    },
    'Сначала новые': {'kk': 'Алдымен жаңалары', 'en': 'Newest first'},
    'Сначала старые': {'kk': 'Алдымен ескiler', 'en': 'Oldest first'},
    'Сумма ↓': {'kk': 'Сома ↓', 'en': 'Amount ↓'},
    'Сумма ↑': {'kk': 'Сома ↑', 'en': 'Amount ↑'},
    'А → Я': {'kk': 'А → Я', 'en': 'A → Z'},
    'Я → А': {'kk': 'Я → А', 'en': 'Z → A'},
    'Дата с': {'kk': 'Күннен', 'en': 'Date from'},
    'Дата по': {'kk': 'Күнге дейін', 'en': 'Date to'},
    'Сумма от': {'kk': 'Сомадан', 'en': 'Amount from'},
    'Сумма до': {'kk': 'Сомаға дейін', 'en': 'Amount to'},
    'Выбрать теги': {'kk': 'Тегтерді таңдау', 'en': 'Select tags'},
    'Нет тегов': {'kk': 'Тегтер жоқ', 'en': 'No tags'},
    'Ничего не найдено по вашему запросу': {
        'kk': 'Сұрауыңыз бойынша ештеңе табылмады',
        'en': 'Nothing found for your query',
    },
    'Связанные документы': {'kk': 'Байланысты құжаттар', 'en': 'Linked documents'},
    'Связанных документов пока нет': {'kk': 'Байланысты құжаттар әлі жоқ', 'en': 'No linked documents yet'},
    'Документы не найдены': {'kk': 'Құжаттар табылмады', 'en': 'No documents found'},
    'Не удалось добавить связь': {'kk': 'Байланыс қосылмады', 'en': 'Could not add link'},
    'Удалить связь': {'kk': 'Байланысты жою', 'en': 'Remove link'},
    'Стр. %(page)s из %(total)s': {'kk': 'Бет %(page)s / %(total)s', 'en': 'Page %(page)s of %(total)s'},
    'Не удалось отобразить страницу': {'kk': 'Бетті көрсету мүмкін болмады', 'en': 'Could not render page'},
    'Не удалось загрузить PDF': {'kk': 'PDF жүктелмedi', 'en': 'Could not load PDF'},
    'Сумма договоров, ₸': {'kk': 'Келісімдер сомасы, ₸', 'en': 'Contract amounts, ₸'},
    'Удалить тег': {'kk': 'Тегті жою', 'en': 'Remove tag'},
    'Печать': {'kk': 'Басып шығару', 'en': 'Print'},
    'Загрузка PDF…': {'kk': 'PDF жүктелуде…', 'en': 'Loading PDF…'},
    'Вход в систему': {'kk': 'Жүйеге кіру', 'en': 'Sign in'},
    'Пароль': {'kk': 'Құпия сөз', 'en': 'Password'},
    'Имя пользователя': {'kk': 'Пайдаланушы аты', 'en': 'Username'},
    'Нет аккаунта? Обратитесь к администратору.': {
        'kk': 'Аккаунт жоқ па? Әкімшіге хабарласыңыз.',
        'en': 'No account? Contact your administrator.',
    },
    'Неверное имя пользователя или пароль.': {
        'kk': 'Пайдаланушы аты немесе құпия сөз дұрыс емес.',
        'en': 'Invalid username or password.',
    },
    'Хранение': {'kk': 'Сақтау', 'en': 'Storage'},
    'Поиск': {'kk': 'Іздеу', 'en': 'Search'},
    'Быстрые действия': {'kk': 'Жылдам әрекеттер', 'en': 'Quick actions'},
    'Создать': {'kk': 'Жасау', 'en': 'Create'},
    'Добавить первый': {'kk': 'Бirinшisін қосу', 'en': 'Add first'},
    'Нет документов.': {'kk': 'Құжаттар жоқ.', 'en': 'No documents.'},
    'Нет категорий.': {'kk': 'Санаттар жоқ.', 'en': 'No categories.'},
    'Просроченных договоров': {'kk': 'Мерзімі өткен келісімдер', 'en': 'Expired contracts'},
    'Динамика сумм': {'kk': 'Сомалар динамикасы', 'en': 'Amount trends'},
    '3 мес': {'kk': '3 ай', 'en': '3 mo'},
    '6 мес': {'kk': '6 ай', 'en': '6 mo'},
    '12 мес': {'kk': '12 ай', 'en': '12 mo'},
    'По категориям': {'kk': 'Санаттар бойынша', 'en': 'By category'},
    'Нет данных за выбранный период': {
        'kk': 'Таңдалған кезеңде деректер жоқ',
        'en': 'No data for the selected period',
    },
    'Имя': {'kk': 'Аты', 'en': 'Name'},
    'Введите имя': {'kk': 'Атын енгізіңіз', 'en': 'Enter name'},
    'Укажите имя.': {'kk': 'Атын көрсетіңіз.', 'en': 'Please enter a name.'},
    'Имя пользователя обновлено: %(name)s.': {
        'kk': 'Пайдаланушы аты жаңартылды: %(name)s.',
        'en': 'User name updated: %(name)s.',
    },
    'Проверьте имя, email и роль.': {
        'kk': 'Аты, email және рөлді тексеріңіз.',
        'en': 'Check name, email, and role.',
    },
    'договор': {'kk': 'келісім', 'en': 'contract'},
    'договора': {'kk': 'келісім', 'en': 'contracts'},
    'договоров': {'kk': 'келісім', 'en': 'contracts'},
}


def should_scan(path: Path) -> bool:
    return path.suffix in {'.py', '.html'} and not any(part in SKIP_PARTS for part in path.parts)


def extract_strings() -> set[str]:
    strings: set[str] = set()
    patterns = [
        re.compile(r"""{%\s*trans\s+['"](.+?)['"]"""),
        re.compile(r"""_\(\s*['"](.+?)['"]"""),
        re.compile(r"""_lazy\(\s*['"](.+?)['"]"""),
        re.compile(r"""{%\s*blocktrans(?:\s+[^%]+)?\s*%}(.+?){%\s*endblocktrans\s*%}""", re.S),
    ]
    for path in BASE_DIR.rglob('*'):
        if not should_scan(path):
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in patterns:
            for match in pattern.finditer(text):
                value = match.group(1).strip()
                value = re.sub(r'\s+', ' ', value)
                if value and not value.startswith('{%') and '{% plural %}' not in value:
                    strings.add(value)
    return strings


def translate(msgid: str, lang: str) -> str:
    if lang == 'ru':
        return msgid
    mapping = {**TRANSLATIONS.get(msgid, {}), **EXTRA_TRANSLATIONS.get(msgid, {})}
    return mapping.get(lang, msgid)


def build_catalog(lang: str, msgids: set[str]) -> polib.POFile:
    po = polib.POFile()
    plural_forms = {
        'ru': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);',
        'en': 'nplurals=2; plural=(n != 1);',
        'kk': 'nplurals=1; plural=0;',
    }
    po.metadata = {
        'Project-Id-Version': 'PDF Data Base',
        'Language': lang,
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Transfer-Encoding': '8bit',
        'Plural-Forms': plural_forms.get(lang, plural_forms['en']),
    }
    for msgid in sorted(msgids):
        entry = polib.POEntry(msgid=msgid, msgstr=translate(msgid, lang))
        po.append(entry)
    add_plural_entries(po, lang)
    return po


def add_plural_entries(catalog: polib.POFile, lang: str) -> None:
    for msgid, data in PLURAL_ENTRIES.items():
        forms = data.get(lang, data['ru'])
        entry = polib.POEntry(msgid=msgid, msgid_plural=data['msgid_plural'])
        if lang == 'en':
            entry.msgstr_plural = {0: forms[0], 1: forms[1]}
        elif lang == 'kk':
            entry.msgstr_plural = {0: forms[0]}
        else:
            entry.msgstr_plural = {0: forms[0], 1: forms[1], 2: forms[2]}
        catalog.append(entry)


PLURAL_ENTRIES = {
    '%(count)d пользователь': {
        'msgid_plural': '%(count)d пользователей',
        'ru': [
            '%(count)d пользователь',
            '%(count)d пользователя',
            '%(count)d пользователей',
        ],
        'en': [
            '%(count)d user',
            '%(count)d users',
        ],
        'kk': [
            '%(count)d пайдаланушы',
        ],
    },
}


def main() -> None:
    msgids = extract_strings()
    for lang in ('ru', 'kk', 'en'):
        catalog = build_catalog(lang, msgids)
        lang_dir = LOCALE_DIR / lang / 'LC_MESSAGES'
        lang_dir.mkdir(parents=True, exist_ok=True)
        po_path = lang_dir / 'django.po'
        mo_path = lang_dir / 'django.mo'
        catalog.save(str(po_path))
        catalog.save_as_mofile(str(mo_path))
        print(f'Wrote {po_path} ({len(catalog)} strings) and {mo_path}')


if __name__ == '__main__':
    main()
