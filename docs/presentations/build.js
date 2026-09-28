// Презентация управляющего слоя QA (ausn-control-plane) и его продукта — фреймворка автотестов ПК АУСН.
// Стиль по образцу «ИИ НА БОЕВОМ ДЕЖУРСТВЕ»: светлый фон #F0F0F0, насыщенный синий #0060F0, тёмный #001030.
const path = require("path");
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.author = "QA-команда ПК АУСН";
pres.title = "Управляющий слой QA для ПК АУСН";

const FONT = "Calibri";
const INK = "001030";
const BRAND = "0060F0";
const BRAND_DARK = "0047B3";
const LIGHT = "F0F2F6";
const CARD = "FFFFFF";
const LINE = "DCE3EE";
const MUTED = "5A6B85";
const OK = "12A150";
const WARN = "E8A400";

const W = 13.333;
const H = 7.5;
const M = 0.6;

const shadow = () => ({ type: "outer", color: "9AA7BD", blur: 8, offset: 2, angle: 90, opacity: 0.25 });

function light(slide) {
  slide.background = { color: LIGHT };
}

function dark(slide) {
  slide.background = { color: INK };
}

function slideTitle(slide, text, subtitle) {
  slide.addText(text, {
    x: M, y: 0.42, w: W - 2 * M, h: 0.62, margin: 0,
    fontFace: FONT, fontSize: 30, bold: true, color: INK, align: "left",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: M, y: 1.02, w: W - 2 * M, h: 0.34, margin: 0,
      fontFace: FONT, fontSize: 14, color: MUTED, align: "left",
    });
  }
}

function pageNumber(slide, index) {
  slide.addText(String(index), {
    x: W - 1.1, y: H - 0.55, w: 0.6, h: 0.3, margin: 0,
    fontFace: FONT, fontSize: 10, color: MUTED, align: "right",
  });
}

function card(slide, x, y, w, h, options = {}) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.07,
    fill: { color: options.fill || CARD },
    line: { color: options.line || LINE, width: options.lineWidth || 1 },
    shadow: options.flat ? undefined : shadow(),
  });
}

function badge(slide, x, y, size, label, options = {}) {
  slide.addShape(pres.ShapeType.ellipse, {
    x, y, w: size, h: size,
    fill: { color: options.fill || BRAND },
    line: { color: options.fill || BRAND, width: 1 },
  });
  slide.addText(label, {
    x, y, w: size, h: size, margin: 0,
    fontFace: FONT, fontSize: options.fontSize || 14, bold: true,
    color: options.color || "FFFFFF", align: "center", valign: "middle",
  });
}

// 1. Титул
const s1 = pres.addSlide();
dark(s1);
s1.addShape(pres.ShapeType.roundRect, {
  x: 0.9, y: 1.5, w: 5.1, h: 0.62, rectRadius: 0.31,
  fill: { color: BRAND }, line: { color: BRAND, width: 1 },
});
s1.addText("QA · управляющий слой", {
  x: 0.9, y: 1.5, w: 5.1, h: 0.62, margin: 0,
  fontFace: FONT, fontSize: 15, bold: true, color: "FFFFFF", align: "center", valign: "middle",
});
s1.addText("Управляющий слой QA\nдля ПК АУСН", {
  x: M, y: 2.35, w: 10.8, h: 1.9, margin: 0,
  fontFace: FONT, fontSize: 46, bold: true, color: "FFFFFF", align: "left", lineSpacing: 48,
});
s1.addText("Как ИИ-агенты управляют качеством и создают фреймворк автотестов", {
  x: M, y: 4.35, w: 9.6, h: 0.5, margin: 0,
  fontFace: FONT, fontSize: 18, color: "9FC0FF", align: "left",
});
s1.addText("ПК АУСН   ·   QA-команда   ·   сентябрь 2026", {
  x: M, y: 6.2, w: 9.0, h: 0.4, margin: 0,
  fontFace: FONT, fontSize: 13, color: "7C8DB0", align: "left",
});
badge(s1, W - 2.1, 2.5, 1.1, "QA", { fill: BRAND, fontSize: 26 });
s1.addNotes("Представление управляющего слоя QA и его результата — фреймворка автотестов ПК АУСН.");

// 2. Контекст и задача
const s2 = pres.addSlide();
light(s2);
slideTitle(s2, "Контекст: что мы тестируем и зачем", "ПК АУСН — кабинет и бэкенд для автоматизированной упрощённой системы налогообложения");
const ctx = [
  ["Что тестируем", "REST API Core и Front Module, Kafka-категоризация операций, интеграции с ФНС и банками, личный кабинет. Стенд ausn-test1.", BRAND],
  ["Проблема", "Знания и правила рассеяны по чатам и страницам, регресс ручной, контракты дрейфуют, результат не воспроизводится между людьми и машинами.", WARN],
  ["Что построили", "Переносимый управляющий слой: правила, навыки, доступы и методология. И продукт — фреймворк автотестов с трассируемостью в Zephyr.", OK],
];
ctx.forEach(([head, text, accent], index) => {
  const x = M + index * 4.12;
  card(s2, x, 1.65, 3.85, 4.9);
  badge(s2, x + 0.32, 1.98, 0.5, String(index + 1), { fill: accent });
  s2.addText(head, {
    x: x + 0.32, y: 2.66, w: 3.2, h: 0.4, margin: 0,
    fontFace: FONT, fontSize: 19, bold: true, color: INK,
  });
  s2.addText(text, {
    x: x + 0.32, y: 3.16, w: 3.2, h: 3.1, margin: 0,
    fontFace: FONT, fontSize: 14, color: MUTED, align: "left", lineSpacing: 20,
  });
});
pageNumber(s2, 2);
s2.addNotes("Задача: закрыть регресс по 41 версии релизов, для каждой принятой задачи иметь тест-кейс, вести актуальную автоматизацию.");

// 3. Что такое управляющий слой
const s3 = pres.addSlide();
light(s3);
slideTitle(s3, "Управляющий слой: что это", "Репозиторий ausn-control-plane — «мозг», а не «руки»: кода продукта в нём нет");
const blocks = [
  ["Правила", "AGENTS.md: модель владения, границы, работа с кодом и данными"],
  ["Навыки", "11 упакованных инструкций для ИИ по зонам QA"],
  ["MCP", "9 серверов доступа к коду, требованиям, стендам и UI"],
  ["Методология", "База QA/SDET и уроки сессий (112 записей)"],
  ["Отчёты", "Разборы, реестры, регламенты — готовые к передаче"],
  ["Переносимость", "Клон на другой машине поднимается за минуты"],
];
blocks.forEach(([head, text], index) => {
  const col = index % 3;
  const row = Math.floor(index / 3);
  const x = M + col * 4.12;
  const y = 1.7 + row * 2.35;
  card(s3, x, y, 3.85, 2.05);
  s3.addText(head, {
    x: x + 0.3, y: y + 0.28, w: 3.25, h: 0.4, margin: 0,
    fontFace: FONT, fontSize: 18, bold: true, color: BRAND,
  });
  s3.addText(text, {
    x: x + 0.3, y: y + 0.78, w: 3.25, h: 1.1, margin: 0,
    fontFace: FONT, fontSize: 13, color: MUTED, lineSpacing: 18,
  });
});
pageNumber(s3, 3);
s3.addNotes("Control plane описывает, как работать: правила, навыки, доступы. Продукт работы — отдельный репозиторий ausn-qa-project.");

// 4. Три контура
const s4 = pres.addSlide();
light(s4);
slideTitle(s4, "Три контура работы", "Источники контракта — только чтение; управляющий слой задаёт правила; продукт создаётся и развивается свободно");
const lanes = [
  ["Источники (read-only)", ["ausn-core, ausn-api, front-module, gateway, frontend, kafka-contracts, admin-*, dbo-emulator, test-stands", "ausn-ai — документационный контекст"], MUTED],
  ["Управляющий слой", ["Правила · навыки · MCP · методология · отчёты", "Индексация контекста и анализ влияния"], BRAND],
  ["Продукт", ["ausn-qa-project: тесты, fixtures, тестовые данные, реестры Zephyr", "Автотесты по слоям пирамиды"], OK],
];
lanes.forEach(([head, items, accent], index) => {
  const y = 1.75 + index * 1.72;
  card(s4, M, y, 7.6, 1.5);
  s4.addShape(pres.ShapeType.roundRect, {
    x: M + 0.28, y: y + 0.3, w: 0.12, h: 0.9, rectRadius: 0.06,
    fill: { color: accent }, line: { color: accent, width: 1 },
  });
  s4.addText(head, {
    x: M + 0.58, y: y + 0.24, w: 6.7, h: 0.34, margin: 0,
    fontFace: FONT, fontSize: 16, bold: true, color: INK,
  });
  s4.addText(items.map((item, i) => ({ text: item, options: { bullet: true, breakLine: i < items.length - 1 } })), {
    x: M + 0.58, y: y + 0.62, w: 6.7, h: 0.78, margin: 0,
    fontFace: FONT, fontSize: 12, color: MUTED, paraSpaceAfter: 4,
  });
});
card(s4, 8.55, 1.75, 4.18, 4.72, { fill: INK, line: INK });
s4.addText("Стенд", {
  x: 8.85, y: 2.02, w: 3.6, h: 0.4, margin: 0,
  fontFace: FONT, fontSize: 18, bold: true, color: "FFFFFF",
});
s4.addText(
  [
    { text: "ausn-test1 (192.168.100.105)", options: { bullet: true, breakLine: true, bold: true } },
    { text: "Core, front-module, categorizer, dbo-integration, admin, gateway-ы банков, iframe-харнесс", options: { bullet: true, breakLine: true } },
    { text: "infra VM (192.168.100.104)", options: { bullet: true, breakLine: true, bold: true } },
    { text: "Keycloak, PostgreSQL, Kafka/Redpanda", options: { bullet: true } },
  ],
  {
    x: 8.85, y: 2.55, w: 3.6, h: 3.5, margin: 0,
    fontFace: FONT, fontSize: 13, color: "C9D6EC", paraSpaceAfter: 8,
  },
);
pageNumber(s4, 4);
s4.addNotes("Все проверки идут на одном стенде ausn-test1; продуктовые репозитории не редактируются — только чтение.");

// 5. Разделитель: MCP
const s5 = pres.addSlide();
dark(s5);
s5.addText("Как агент взаимодействует\nс системой", {
  x: M, y: 2.5, w: 10.8, h: 1.7, margin: 0,
  fontFace: FONT, fontSize: 40, bold: true, color: "FFFFFF", lineSpacing: 44,
});
s5.addText("MCP: код, требования, репозитории, стенды и UI — через единый набор инструментов", {
  x: M, y: 4.3, w: 10.8, h: 0.5, margin: 0,
  fontFace: FONT, fontSize: 17, color: "9FC0FF",
});
badge(s5, W - 2.1, 2.7, 1.1, "MCP", { fill: BRAND, fontSize: 20 });
s5.addNotes("Раздел о том, какими инструментами управляющий слой получает доступ к данным и среде.");

// 6. MCP-серверы
const s6 = pres.addSlide();
light(s6);
slideTitle(s6, "Девять MCP-серверов — пять групп задач", "Один набор — четыре клиента (opencode, Codex, VS Code, совместимые); расхождения ловит гейт паритета");
const groups = [
  ["Код и контекст", "SocratiCode", "семантический поиск, символы, граф, анализ влияния"],
  ["Требования", "Atlassian", "Jira и Confluence: задачи, релизы, требования"],
  ["Репозитории", "GitLab", "файлы по ref, диффы, коммиты, MR"],
  ["Стенды", "SSH · PostgreSQL · Graylog · Grafana", "контейнеры и логи, данные, метрики"],
  ["UI и связь", "Playwright · Mattermost", "сценарии в браузере, уведомления команды"],
];
groups.forEach(([head, servers, text], index) => {
  const col = index % 3;
  const row = Math.floor(index / 3);
  const x = M + col * 4.12;
  const y = 1.7 + row * 2.4;
  card(s6, x, y, 3.85, 2.1);
  s6.addText(head, {
    x: x + 0.3, y: y + 0.24, w: 3.25, h: 0.32, margin: 0,
    fontFace: FONT, fontSize: 13, bold: true, color: MUTED,
  });
  s6.addText(servers, {
    x: x + 0.3, y: y + 0.6, w: 3.25, h: 0.62, margin: 0,
    fontFace: FONT, fontSize: 15, bold: true, color: BRAND, lineSpacing: 18,
  });
  s6.addText(text, {
    x: x + 0.3, y: y + 1.28, w: 3.25, h: 0.7, margin: 0,
    fontFace: FONT, fontSize: 12, color: MUTED, lineSpacing: 16,
  });
});
card(s6, M + 4.12, 4.1, 3.85, 2.1, { fill: INK, line: INK });
s6.addText("Гейт паритета", {
  x: M + 4.42, y: 4.34, w: 3.25, h: 0.34, margin: 0,
  fontFace: FONT, fontSize: 14, bold: true, color: "FFFFFF",
});
s6.addText("Конфигурации четырёх клиентов сверяются автоматически: дрейф доступа не остаётся незамеченным.", {
  x: M + 4.42, y: 4.74, w: 3.25, h: 1.1, margin: 0,
  fontFace: FONT, fontSize: 13, color: "C9D6EC", lineSpacing: 18,
});
pageNumber(s6, 6);
s6.addNotes("Секреты хранятся только в локальном .env; запуск — из корня управляющего слоя; кэш авторизации локален.");

// 7. SocratiCode
const s7 = pres.addSlide();
light(s7);
slideTitle(s7, "Контекст кода: индексация и анализ влияния", "SocratiCode + локальные эмбеддинги: код не покидает машину");
const stats7 = [
  ["15", "проектов в индексе"],
  ["~8,9 тыс.", "файлов проиндексировано"],
  ["516", "чанков навыков и агентов"],
];
stats7.forEach(([value, label], index) => {
  const x = M + index * 4.12;
  card(s7, x, 1.7, 3.85, 1.75);
  s7.addText(value, {
    x: x + 0.3, y: 1.9, w: 3.25, h: 0.75, margin: 0,
    fontFace: FONT, fontSize: 40, bold: true, color: BRAND,
  });
  s7.addText(label, {
    x: x + 0.3, y: 2.72, w: 3.25, h: 0.55, margin: 0,
    fontFace: FONT, fontSize: 13, color: MUTED,
  });
});
card(s7, M, 3.7, 12.13, 2.85);
s7.addText("Что это даёт", {
  x: M + 0.35, y: 3.95, w: 11.4, h: 0.36, margin: 0,
  fontFace: FONT, fontSize: 18, bold: true, color: INK,
});
s7.addText(
  [
    { text: "Ожидаемое поведение берём из кода продукта, а не из пересказа — оракул не подменяется.", options: { bullet: true, breakLine: true } },
    { text: "Перед правкой теста агент видит «радиус поражения»: кто зависит от функции и какие тесты затронуты.", options: { bullet: true, breakLine: true } },
    { text: "Поиск по 15 репозиториям, включая наш фреймворк — ревью тестов и повторное использование кода.", options: { bullet: true, breakLine: true } },
    { text: "Навыки и субагенты индексируются как контекст: ИИ находит нужную инструкцию до начала работы.", options: { bullet: true } },
  ],
  {
    x: M + 0.35, y: 4.42, w: 11.4, h: 2.0, margin: 0,
    fontFace: FONT, fontSize: 14, color: MUTED, paraSpaceAfter: 10,
  },
);
pageNumber(s7, 7);
s7.addNotes("Индексация локальная (Ollama, nomic-embed-text). Qdrant — локальный контейнер, данные вне Git.");

// 8. Навыки и субагенты
const s8 = pres.addSlide();
light(s8);
slideTitle(s8, "Навыки и субагенты", "Навык — упакованная инструкция; субагент — роль с ограниченной зоной ответственности");
card(s8, M, 1.7, 7.6, 4.85);
s8.addText("11 навыков", {
  x: M + 0.35, y: 1.95, w: 6.9, h: 0.36, margin: 0,
  fontFace: FONT, fontSize: 18, bold: true, color: INK,
});
s8.addText(
  [
    { text: "ausn-qa-loop — основной процесс: contract-first loop", options: { bullet: true, breakLine: true } },
    { text: "ausn-socraticode — работа с кодом связанных проектов", options: { bullet: true, breakLine: true } },
    { text: "ausn-qa-mcp — выбор и границы MCP-инструментов", options: { bullet: true, breakLine: true } },
    { text: "ausn-qa-methodology — тест-дизайн и доказательства", options: { bullet: true, breakLine: true } },
    { text: "ausn-api-contract-testing, ausn-source-driven-development", options: { bullet: true, breakLine: true } },
    { text: "ausn-categorizer-lifecycle, ausn-postman-sync", options: { bullet: true, breakLine: true } },
    { text: "ausn-qa-agents, ausn-context-engineering, karpathy-guidelines", options: { bullet: true } },
  ],
  {
    x: M + 0.35, y: 2.45, w: 6.9, h: 3.9, margin: 0,
    fontFace: FONT, fontSize: 13.5, color: MUTED, paraSpaceAfter: 9,
  },
);
card(s8, 8.55, 1.7, 4.18, 4.85);
s8.addText("7 субагентов", {
  x: 8.85, y: 1.95, w: 3.6, h: 0.36, margin: 0,
  fontFace: FONT, fontSize: 18, bold: true, color: INK,
});
s8.addText(
  [
    { text: "contract-research — источник контракта", options: { bullet: true, breakLine: true } },
    { text: "test-design — сценарии и данные", options: { bullet: true, breakLine: true } },
    { text: "test-implementation — реализация тестов", options: { bullet: true, breakLine: true } },
    { text: "review — независимая проверка", options: { bullet: true, breakLine: true } },
    { text: "ci-triage — разбор падений", options: { bullet: true, breakLine: true } },
    { text: "test-maintenance — flaky и устаревшее", options: { bullet: true, breakLine: true } },
    { text: "docs — документация", options: { bullet: true } },
  ],
  {
    x: 8.85, y: 2.45, w: 3.6, h: 3.9, margin: 0,
    fontFace: FONT, fontSize: 13.5, color: MUTED, paraSpaceAfter: 9,
  },
);
pageNumber(s8, 8);
s8.addNotes("Маршрут ролей: исследование контракта → дизайн → реализация → ревью. Команда /qa-task запускает ежедневный цикл.");

// 9. Разделитель: продукт
const s9 = pres.addSlide();
dark(s9);
s9.addText("Как создаётся продукт", {
  x: M, y: 2.6, w: 10.8, h: 0.9, margin: 0,
  fontFace: FONT, fontSize: 40, bold: true, color: "FFFFFF",
});
s9.addText("Contract-first QA loop: от источника контракта до кейса в Zephyr", {
  x: M, y: 3.65, w: 10.8, h: 0.5, margin: 0,
  fontFace: FONT, fontSize: 17, color: "9FC0FF",
});
badge(s9, W - 2.1, 2.75, 1.1, "→", { fill: BRAND, fontSize: 26 });
s9.addNotes("Раздел о том, как из задачи появляется тест, кейс и подтверждённый результат.");

// 10. Цикл
const s10 = pres.addSlide();
light(s10);
slideTitle(s10, "Цикл: от задачи до подтверждённого результата", "Каждый шаг фиксируется в ledger — видно, что проверено и с каким исходом");
const steps = [
  ["1", "Задача Jira", "требование и границы"],
  ["2", "Источник контракта", "модели и код продукта"],
  ["3", "Ledger кейсов", "план и статусы проверок"],
  ["4", "Тест-дизайн", "сценарии и данные"],
  ["5", "Прогон", "данные → окружение → продукт"],
  ["6", "Zephyr", "кейс + привязка + прогон"],
];
steps.forEach(([num, head, text], index) => {
  const col = index % 3;
  const row = Math.floor(index / 3);
  const x = M + col * 4.12;
  const y = 1.75 + row * 2.0;
  card(s10, x, y, 3.85, 1.7);
  badge(s10, x + 0.3, y + 0.3, 0.46, num, { fill: BRAND });
  s10.addText(head, {
    x: x + 0.92, y: y + 0.3, w: 2.6, h: 0.4, margin: 0,
    fontFace: FONT, fontSize: 16, bold: true, color: INK,
  });
  s10.addText(text, {
    x: x + 0.92, y: y + 0.74, w: 2.6, h: 0.75, margin: 0,
    fontFace: FONT, fontSize: 13, color: MUTED, lineSpacing: 17,
  });
});
card(s10, M, 5.85, 12.13, 1.05, { fill: "E4EEFF", line: "C9DCFF" });
s10.addText("Трассируемость: 521 связь кейсов с 417 задачами Jira — у каждой принятой задачи есть кейс и прогон.", {
  x: M + 0.35, y: 6.08, w: 11.4, h: 0.6, margin: 0,
  fontFace: FONT, fontSize: 14, bold: true, color: BRAND_DARK, valign: "middle",
});
pageNumber(s10, 10);
s10.addNotes("Ledger — markdown-файл с таблицей кейсов и статусами; provenance-шапка связывает его с задачами Jira.");

// 11. Продукт: фреймворк
const s11 = pres.addSlide();
light(s11);
slideTitle(s11, "Продукт: фреймворк автотестов по слоям", "Пирамида проверок: от дешёвых эталонов до сквозных UI-сценариев");
const layerRows = [
  ["Contract", "статические проверки и эталоны", "tests/static + characterization"],
  ["API", "контрактные REST-проверки по UC", "tests/api"],
  ["DB/Tooling", "БД и tooling-controller", "tests/db, tests/tooling"],
  ["Integration", "Kafka, категоризация, Фактура", "tests/kafka, tests/integration"],
  ["UI/E2E", "браузерные сценарии (Playwright)", "tests/ui"],
];
layerRows.forEach(([layer, text, path_], index) => {
  const y = 1.72 + index * 0.78;
  card(s11, M, y, 7.7, 0.68);
  s11.addText(layer, {
    x: M + 0.28, y: y + 0.16, w: 1.55, h: 0.36, margin: 0,
    fontFace: FONT, fontSize: 15, bold: true, color: BRAND,
  });
  s11.addText(text, {
    x: M + 1.9, y: y + 0.16, w: 3.1, h: 0.4, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: INK,
  });
  s11.addText(path_, {
    x: M + 5.1, y: y + 0.19, w: 2.45, h: 0.36, margin: 0,
    fontFace: "Consolas", fontSize: 10.5, color: MUTED,
  });
});
card(s11, 8.55, 1.72, 4.18, 3.5, { fill: INK, line: INK });
s11.addText("Non-automated", {
  x: 8.85, y: 1.96, w: 3.6, h: 0.36, margin: 0,
  fontFace: FONT, fontSize: 15, bold: true, color: "FFFFFF",
});
s11.addText("Процессные, инфраструктурные и ручные визуальные проверки — видны в плане как Blocked с причиной, а не как «покрыто».", {
  x: 8.85, y: 2.4, w: 3.6, h: 1.4, margin: 0,
  fontFace: FONT, fontSize: 13, color: "C9D6EC", lineSpacing: 18,
});
s11.addText("Гейты качества", {
  x: 8.85, y: 3.85, w: 3.6, h: 0.34, margin: 0,
  fontFace: FONT, fontSize: 14, bold: true, color: "FFFFFF",
});
s11.addText("audit_gate 11/11 · smoke_gate GREEN/RED · контроль кодировок · карта репозитория", {
  x: 8.85, y: 4.2, w: 3.6, h: 0.9, margin: 0,
  fontFace: FONT, fontSize: 12.5, color: "9FC0FF", lineSpacing: 17,
});
card(s11, M, 5.75, 7.7, 1.15, { fill: "E4EEFF", line: "C9DCFF" });
s11.addText("Артефакты: файлы тестов, fixtures, тестовые данные, реестры Zephyr и отчёты — всё в одном репозитории.", {
  x: M + 0.3, y: 5.98, w: 7.1, h: 0.7, margin: 0,
  fontFace: FONT, fontSize: 13, color: BRAND_DARK, valign: "middle",
});
pageNumber(s11, 11);
s11.addNotes("Фреймворк pytest: клиенты HTTP/DB/Kafka, Pydantic-модели, общие фикстуры, гейты перед коммитом.");

// 12. Результаты: покрытие
const s12 = pres.addSlide();
light(s12);
slideTitle(s12, "Результат: покрытие и трассируемость", "Актуальная автоматизация, а не архив закрытых релизов");
const stats12 = [
  ["381", "тест-кейс в Zephyr"],
  ["521", "связь с 417 задачами"],
  ["41", "версий релизов в аудите"],
];
stats12.forEach(([value, label], index) => {
  const x = M + index * 2.9;
  card(s12, x, 1.7, 2.65, 2.0);
  s12.addText(value, {
    x: x + 0.25, y: 1.92, w: 2.15, h: 0.8, margin: 0,
    fontFace: FONT, fontSize: 40, bold: true, color: BRAND,
  });
  s12.addText(label, {
    x: x + 0.25, y: 2.85, w: 2.15, h: 0.7, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED, lineSpacing: 16,
  });
});
card(s12, 9.45, 1.7, 3.28, 4.9, { fill: CARD, line: LINE });
s12.addChart(
  pres.ChartType.doughnut,
  [{ name: "Приоритет", labels: ["High (P0/P1)", "Normal (P2)", "Low (P3)"], values: [224, 122, 35] }],
  {
    x: 9.55, y: 2.1, w: 3.08, h: 3.1,
    showTitle: true, title: "Приоритет кейсов", titleFontSize: 13, titleColor: INK,
    showLegend: true, legendPos: "b", legendFontSize: 10, legendColor: MUTED,
    chartColors: [BRAND, "5B9BD5", "A5A5A5"],
    showValue: false, holeSize: 60, dataBorder: { pt: 1, color: "FFFFFF" },
  },
);
card(s12, M, 3.9, 8.55, 2.7);
s12.addText("Покрытие по слоям", {
  x: M + 0.3, y: 4.12, w: 7.9, h: 0.36, margin: 0,
  fontFace: FONT, fontSize: 16, bold: true, color: INK,
});
s12.addText(
  [
    { text: "Категоризатор: 104 правила из БД — включённые покрыты полностью.", options: { bullet: true, breakLine: true } },
    { text: "Use Cases кабинета: UC-01…UC-25, админ-контур, роли банков, отчёты, платежи.", options: { bullet: true, breakLine: true } },
    { text: "Функциональная структура папок: 31 раздел, 8 компонентов продукта.", options: { bullet: true } },
  ],
  {
    x: M + 0.3, y: 4.55, w: 7.9, h: 1.9, margin: 0,
    fontFace: FONT, fontSize: 13, color: MUTED, paraSpaceAfter: 8,
  },
);
pageNumber(s12, 12);
s12.addNotes("Кейсы и связи живут в Zephyr Scale (Jira PKAUSN); структура папок отражает текущий функционал, а не историю релизов.");

// 13. Результаты: стабильность
const s13 = pres.addSlide();
light(s13);
slideTitle(s13, "Результат: наборы зелёные, падений нет", "Прогоны 2026-09-25; skip/xfail — только с явной причиной (среда или отсутствие данных)");
card(s13, M, 1.7, 12.13, 3.3);
s13.addChart(
  pres.ChartType.bar,
  [
    {
      name: "Пройдено",
      labels: ["API", "Категоризатор", "Contract · DB · Tooling · Unit", "UI/E2E"],
      values: [457, 687, 425, 33],
    },
  ],
  {
    x: M + 0.25, y: 1.95, w: 11.6, h: 2.9,
    barDir: "bar", barGapWidthPct: 60, chartColors: [BRAND],
    showTitle: false, showLegend: false, showValue: true, dataLabelPosition: "outEnd",
    dataLabelFontSize: 12, dataLabelColor: INK, dataLabelFontBold: true,
    catAxisLabelColor: INK, catAxisLabelFontSize: 12,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 11,
    valGridLine: { color: "E6ECF5", size: 1 }, catGridLine: { style: "none" },
    valAxisMaxVal: 750,
  },
);
const notes13 = [
  ["0 падений", "во всех слоях — Fail = 0"],
  ["3,2 мин", "быстрый smoke-гейт (273 passed)"],
  ["GREEN", "вердикт автоматического гейта"],
];
notes13.forEach(([value, label], index) => {
  const x = M + index * 4.12;
  card(s13, x, 5.2, 3.85, 1.7);
  s13.addText(value, {
    x: x + 0.3, y: 5.4, w: 3.25, h: 0.6, margin: 0,
    fontFace: FONT, fontSize: 26, bold: true, color: OK,
  });
  s13.addText(label, {
    x: x + 0.3, y: 6.05, w: 3.25, h: 0.6, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED, lineSpacing: 16,
  });
});
pageNumber(s13, 13);
s13.addNotes("Числа — фактический прогон 25.09.2026; расхождения сборки стенда документируются и превращаются в skip с причиной.");

// 14. Результаты: регресс
const s14 = pres.addSlide();
light(s14);
slideTitle(s14, "Результат: регресс как управляемая система", "План состоит из прогонов по слоям — Smoke для скорости, Full для полноты");
const plans = [
  ["PKAUSN-P4", "AUSN Регресс 2.0", "11 прогонов по слоям", "525 Pass · 0 Fail · 80 Blocked с причиной"],
  ["PKAUSN-P5", "AUSN Smoke (High)", "5 прогонов, только High", "206 Pass · 0 Fail · 18 Blocked с причиной"],
];
plans.forEach(([key, name, scope, result], index) => {
  const y = 1.72 + index * 1.72;
  card(s14, M, y, 7.7, 1.5);
  s14.addText(key, {
    x: M + 0.3, y: y + 0.22, w: 2.2, h: 0.36, margin: 0,
    fontFace: FONT, fontSize: 16, bold: true, color: BRAND,
  });
  s14.addText(name, {
    x: M + 2.5, y: y + 0.24, w: 4.9, h: 0.34, margin: 0,
    fontFace: FONT, fontSize: 14, bold: true, color: INK,
  });
  s14.addText(`${scope}   ·   ${result}`, {
    x: M + 0.3, y: y + 0.72, w: 7.0, h: 0.6, margin: 0,
    fontFace: FONT, fontSize: 13, color: MUTED,
  });
});
card(s14, 8.55, 1.72, 4.18, 3.2, { fill: INK, line: INK });
s14.addText("Критерии выхода", {
  x: 8.85, y: 1.96, w: 3.6, h: 0.34, margin: 0,
  fontFace: FONT, fontSize: 15, bold: true, color: "FFFFFF",
});
s14.addText(
  [
    { text: "Fail = 0 в обоих планах", options: { bullet: true, breakLine: true } },
    { text: "Каждый Blocked — с причиной: нет автоматизации, среда, ожидание джоб", options: { bullet: true, breakLine: true } },
    { text: "Повторный запуск добавляет только новые кейсы (дельта-прогоны)", options: { bullet: true } },
  ],
  {
    x: 8.85, y: 2.42, w: 3.6, h: 2.3, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: "C9D6EC", paraSpaceAfter: 8,
  },
);
card(s14, M, 5.15, 7.7, 1.75, { fill: "E4EEFF", line: "C9DCFF" });
s14.addText("Порядок разбора падений: тестовые данные → окружение → продукт.", {
  x: M + 0.3, y: 5.35, w: 7.1, h: 0.36, margin: 0,
  fontFace: FONT, fontSize: 14, bold: true, color: BRAND_DARK,
});
s14.addText("Среда не маскируется «зелёным»: ограничения стенда фиксируются отчётом и снимаются после обновления сборки.", {
  x: M + 0.3, y: 5.78, w: 7.1, h: 0.9, margin: 0,
  fontFace: FONT, fontSize: 12.5, color: MUTED, lineSpacing: 17,
});
pageNumber(s14, 14);
s14.addNotes("Регламент регресса и smoke-гейта — в репозитории продукта, docs/reports/regression-process.md.");

// 15. Находки
const s15 = pres.addSlide();
light(s15);
slideTitle(s15, "Что нашёл управляемый QA-процесс", "Дефекты и дрейфы, подтверждённые прогонами и логами");
const findings = [
  ["NPE на главном экране", "GET /operation/recent → 500 в стендовой сборке (в develop исправлено) — дефект зафиксирован с трассировкой.", BRAND],
  ["405 вместо 404", "Маркер xfail снят после подтверждённого исправления продукта: тест перевернулся, покрытие стало честным.", OK],
  ["Утечка внутренних данных", "Read-side маскирование refusalToAccept: дефект от 02.07 закрыт прогоном 25.09 (TESTED_PASSING).", OK],
  ["Дрейф сборки стенда", "Роли, статусы и поведение расходятся с develop — отчёт команде и управляемые skip вместо ложных падений.", WARN],
];
findings.forEach(([head, text, accent], index) => {
  const y = 1.72 + index * 1.25;
  card(s15, M, y, 12.13, 1.1);
  s15.addShape(pres.ShapeType.ellipse, {
    x: M + 0.32, y: y + 0.33, w: 0.44, h: 0.44,
    fill: { color: accent }, line: { color: accent, width: 1 },
  });
  s15.addText(head, {
    x: M + 1.0, y: y + 0.16, w: 4.1, h: 0.36, margin: 0,
    fontFace: FONT, fontSize: 15, bold: true, color: INK,
  });
  s15.addText(text, {
    x: M + 5.3, y: y + 0.14, w: 6.5, h: 0.85, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED, lineSpacing: 16, valign: "middle",
  });
});
card(s15, M, 6.1, 12.13, 0.85, { fill: INK, line: INK });
s15.addText("Ценность: дефект не «теряется» — он либо исправлен и подтверждён прогоном, либо заведён с кейсом и доказательством.", {
  x: M + 0.3, y: 6.28, w: 11.5, h: 0.5, margin: 0,
  fontFace: FONT, fontSize: 13.5, color: "C9D6EC", valign: "middle",
});
pageNumber(s15, 15);
s15.addNotes("Публикации в Jira/Confluence делает человек; управляющий слой готовит текст и доказательства.");

// 16. Итоги
const s16 = pres.addSlide();
dark(s16);
s16.addText("Итоги", {
  x: M, y: 0.7, w: 10.0, h: 0.75, margin: 0,
  fontFace: FONT, fontSize: 36, bold: true, color: "FFFFFF",
});
const totals = [
  ["Управляемый процесс", "Правила, навыки и доступы в одном переносимом репозитории; ИИ работает по инструкциям, а не по памяти."],
  ["Продукт", "Фреймворк автотестов по слоям: 381 кейс, 0 падений, прогоны по слоям и быстрый smoke-гейт."],
  ["Трассируемость", "521 связь кейсов с 417 задачами: у каждой принятой задачи есть кейс и подтверждённый прогон."],
  ["Управление знаниями", "112 уроков сессий, регламенты и отчёты — опыт не уходит вместе с человеком."],
];
totals.forEach(([head, text], index) => {
  const col = index % 2;
  const row = Math.floor(index / 2);
  const x = M + col * 6.15;
  const y = 1.75 + row * 2.15;
  card(s16, x, y, 5.85, 1.9, { fill: "0B1E42", line: "1B3A6B", flat: true });
  s16.addText(head, {
    x: x + 0.35, y: y + 0.26, w: 5.15, h: 0.4, margin: 0,
    fontFace: FONT, fontSize: 17, bold: true, color: "FFFFFF",
  });
  s16.addText(text, {
    x: x + 0.35, y: y + 0.72, w: 5.15, h: 1.0, margin: 0,
    fontFace: FONT, fontSize: 13, color: "C9D6EC", lineSpacing: 18,
  });
});
s16.addText("Дальше: визуальный UI-скоуп · управляемые триггеры для EOM и СКБ · подготовка тестовых данных · расширение покрытия в CI", {
  x: M, y: 6.25, w: 11.5, h: 0.5, margin: 0,
  fontFace: FONT, fontSize: 13.5, color: "9FC0FF",
});
s16.addNotes("Итог: управляющий слой превращает разрозненную QA-работу в переносимую, проверяемую систему.");

const output = path.join(__dirname, "ausn-control-plane.pptx");
pres.writeFile({ fileName: output }).then(() => console.log("written:", output));
