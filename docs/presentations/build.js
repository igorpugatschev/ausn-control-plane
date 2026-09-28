// Презентация управляющего слоя QA и продукта (фреймворк автотестов ПК АУСН).
// Диаграммы — нативные фигуры PowerPoint: архитектура, MCP-шина, sequence, activity, пирамида слоёв.
// Стиль по образцу: светлый фон, синий акцент #0060F0, тёмный #001030.
const path = require("path");
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5

const FONT = "Calibri";
const INK = "001030";
const BRAND = "0060F0";
const BRAND_DARK = "0047B3";
const BRAND_SOFT = "E4EEFF";
const BRAND_LINE = "C9DCFF";
const LIGHT = "F0F2F6";
const CARD = "FFFFFF";
const LINE = "DCE3EE";
const MUTED = "5A6B85";
const OK = "12A150";
const WARN = "E8A400";
const PANEL = "0B1E42";
const PANEL_LINE = "1B3A6B";
const PANEL_TEXT = "C9D6EC";

const W = 13.333;
const H = 7.5;
const M = 0.6;

const shadow = () => ({ type: "outer", color: "9AA7BD", blur: 8, offset: 2, angle: 90, opacity: 0.22 });

function light(slide) {
  slide.background = { color: LIGHT };
}
function dark(slide) {
  slide.background = { color: INK };
}

function slideTitle(slide, text, subtitle) {
  slide.addText(text, {
    x: M, y: 0.38, w: W - 2 * M, h: 0.6, margin: 0,
    fontFace: FONT, fontSize: 28, bold: true, color: INK, align: "left",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: M, y: 0.98, w: W - 2 * M, h: 0.34, margin: 0,
      fontFace: FONT, fontSize: 13.5, color: MUTED, align: "left",
    });
  }
}

function pageNumber(slide, index) {
  slide.addText(String(index), {
    x: W - 1.1, y: H - 0.52, w: 0.6, h: 0.3, margin: 0,
    fontFace: FONT, fontSize: 10, color: MUTED, align: "right",
  });
}

function card(slide, x, y, w, h, options = {}) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: options.radius === undefined ? 0.07 : options.radius,
    fill: { color: options.fill || CARD },
    line: { color: options.line || LINE, width: options.lineWidth === undefined ? 1 : options.lineWidth },
    shadow: options.flat ? undefined : shadow(),
  });
}

function badge(slide, x, y, size, label, options = {}) {
  slide.addShape(pres.ShapeType.ellipse, {
    x, y, w: size, h: size,
    fill: { color: options.fill || BRAND }, line: { color: options.fill || BRAND, width: 1 },
  });
  slide.addText(label, {
    x, y, w: size, h: size, margin: 0,
    fontFace: FONT, fontSize: options.fontSize || 13, bold: true,
    color: options.color || "FFFFFF", align: "center", valign: "middle",
  });
}

// Стрелка-коннектор между точками (обе точки в дюймах).
function arrow(slide, x1, y1, x2, y2, options = {}) {
  const left = Math.min(x1, x2);
  const top = Math.min(y1, y2);
  slide.addShape(pres.ShapeType.line, {
    x: left, y: top, w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    line: {
      color: options.color || BRAND,
      width: options.width || 1.5,
      dashType: options.dash ? "dash" : "solid",
      beginArrowType: x2 < x1 ? "triangle" : "none",
      endArrowType: y2 > y1 || x2 > x1 ? "triangle" : "none",
    },
    shadow: undefined,
  });
  if (options.label) {
    const midX = (x1 + x2) / 2;
    const labelWidth = Math.max(Math.abs(x2 - x1) + 0.6, 1.6);
    slide.addText(options.label, {
      x: midX - labelWidth / 2, y: Math.min(y1, y2) - 0.28, w: labelWidth, h: 0.24, margin: 0,
      fontFace: FONT, fontSize: 10, color: MUTED, align: "center",
    });
  }
}

function hline(slide, x1, x2, y, options = {}) {
  slide.addShape(pres.ShapeType.line, {
    x: Math.min(x1, x2), y, w: Math.abs(x2 - x1), h: 0.01,
    line: {
      color: options.color || BRAND, width: options.width || 1.5,
      dashType: options.dash ? "dash" : "solid",
      beginArrowType: options.beginArrow ? "triangle" : "none",
      endArrowType: options.endArrow === false ? "none" : "triangle",
    },
  });
}

function vline(slide, x, y1, y2, options = {}) {
  slide.addShape(pres.ShapeType.line, {
    x, y: Math.min(y1, y2), w: 0.01, h: Math.abs(y2 - y1),
    line: {
      color: options.color || BRAND, width: options.width || 1.5,
      dashType: options.dash ? "dash" : "solid",
      beginArrowType: options.beginArrow ? "triangle" : "none",
      endArrowType: options.endArrow === false ? "none" : "triangle",
    },
  });
}

function doubleArrow(slide, x1, y1, x2, y2, options = {}) {
  slide.addShape(pres.ShapeType.line, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1) || 0.01,
    line: {
      color: options.color || BRAND, width: options.width || 1.5,
      dashType: options.dash ? "dash" : "solid",
      beginArrowType: "triangle", endArrowType: "triangle",
    },
  });
}

function nodeBox(slide, x, y, w, h, title, subtitle, options = {}) {
  card(slide, x, y, w, h, { fill: options.fill || CARD, line: options.line || LINE, flat: options.flat });
  slide.addText(title, {
    x: x + 0.16, y: y + (subtitle ? 0.16 : 0), w: w - 0.32, h: subtitle ? 0.32 : h, margin: 0,
    fontFace: FONT, fontSize: options.fontSize || 13, bold: true,
    color: options.color || INK, align: "center", valign: subtitle ? "top" : "middle",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: x + 0.16, y: y + 0.48, w: w - 0.32, h: h - 0.56, margin: 0,
      fontFace: FONT, fontSize: options.subSize || 11, color: options.subColor || MUTED,
      align: "center", valign: "top", lineSpacing: 14,
    });
  }
}

// 1. Титул
const s1 = pres.addSlide();
dark(s1);
s1.addShape(pres.ShapeType.roundRect, {
  x: 0.9, y: 1.45, w: 4.7, h: 0.6, rectRadius: 0.3,
  fill: { color: BRAND }, line: { color: BRAND, width: 1 },
});
s1.addText("QA · управляющий слой", {
  x: 0.9, y: 1.45, w: 4.7, h: 0.6, margin: 0,
  fontFace: FONT, fontSize: 15, bold: true, color: "FFFFFF", align: "center", valign: "middle",
});
s1.addText("Управляющий слой QA\nдля ПК АУСН", {
  x: M, y: 2.3, w: 10.8, h: 1.9, margin: 0,
  fontFace: FONT, fontSize: 44, bold: true, color: "FFFFFF", lineSpacing: 46,
});
s1.addText("Как ИИ-агенты управляют качеством и создают фреймворк автотестов", {
  x: M, y: 4.32, w: 10.0, h: 0.5, margin: 0,
  fontFace: FONT, fontSize: 17, color: "9FC0FF",
});
s1.addText("ПК АУСН   ·   QA-команда   ·   сентябрь 2026", {
  x: M, y: 6.15, w: 9.0, h: 0.4, margin: 0,
  fontFace: FONT, fontSize: 13, color: "7C8DB0",
});
badge(s1, W - 2.15, 2.45, 1.15, "QA", { fill: BRAND, fontSize: 26 });
s1.addNotes(
  "[~1 мин] Приветствие. Цель: показать управляющий слой (как устроена работа QA с ИИ) и его результат — " +
  "фреймворк автотестов. Регламент 30–45 мин: 19 слайдов + вопросы. Аудитория смешанная — термины объясняю по ходу, " +
  "технические детали и точные цифры — в заметках к слайдам.",
);

// 2. Маршрут
const s2 = pres.addSlide();
light(s2);
slideTitle(s2, "Маршрут", "Четыре вопроса, на которые отвечает эта презентация");
const route = [
  ["1", "Что это", "Управляющий слой: правила и инструкции для ИИ, доступы к системам, методология."],
  ["2", "Как работает", "Как агент получает доступ к коду, задачам и стендам; как устроен цикл проверки."],
  ["3", "Что создаёт", "Фреймворк автотестов: слои, тестовые данные, трассируемость в Zephyr."],
  ["4", "Что получилось", "Результаты, найденные дефекты и что дальше."],
];
route.forEach(([num, head, text], index) => {
  const col = index % 2;
  const row = Math.floor(index / 2);
  const x = M + col * 6.15;
  const y = 1.75 + row * 2.35;
  card(s2, x, y, 5.85, 2.1);
  badge(s2, x + 0.34, y + 0.34, 0.52, num, { fill: BRAND });
  s2.addText(head, {
    x: x + 1.05, y: y + 0.32, w: 4.5, h: 0.4, margin: 0,
    fontFace: FONT, fontSize: 19, bold: true, color: INK,
  });
  s2.addText(text, {
    x: x + 1.05, y: y + 0.86, w: 4.5, h: 1.05, margin: 0,
    fontFace: FONT, fontSize: 13.5, color: MUTED, lineSpacing: 19,
  });
});
pageNumber(s2, 2);
s2.addNotes("[~1 мин] Каркас выступления. Термины (MCP, навык, субагент, ledger) разберу на слайде 4.");

// 3. Контекст
const s3 = pres.addSlide();
light(s3);
slideTitle(s3, "Что мы тестируем", "ПК АУСН — сервис для автоматизированной упрощённой системы налогообложения");
const ctx = [
  ["Продукт", "Личный кабинет налогоплательщика и его бэкенд: API, операции, уведомления, отчёты, роли банков.", BRAND],
  ["Интеграции", "Обмен с ФНС и банками; поток операций через Kafka; категоризация операций правилами из базы.", "5B9BD5"],
  ["Проверяем на стенде", "Один стенд ausn-test1: сервисы, база, брокер сообщений, административный контур и UI банка.", "7030A0"],
];
ctx.forEach(([head, text, accent], index) => {
  const x = M + index * 4.12;
  card(s3, x, 1.75, 3.85, 4.6);
  badge(s3, x + 0.32, 2.08, 0.5, String(index + 1), { fill: accent });
  s3.addText(head, {
    x: x + 0.32, y: 2.76, w: 3.2, h: 0.4, margin: 0,
    fontFace: FONT, fontSize: 18, bold: true, color: INK,
  });
  s3.addText(text, {
    x: x + 0.32, y: 3.26, w: 3.2, h: 2.9, margin: 0,
    fontFace: FONT, fontSize: 14, color: MUTED, lineSpacing: 20,
  });
});
pageNumber(s3, 3);
s3.addNotes(
  "[~1 мин] Продукт — кабинет налогоплательщика и бэкенд; интеграции с ФНС и банками; операции идут потоком через Kafka " +
  "и раскладываются по правилам из базы. Стенд один — ausn-test1 (192.168.100.105), инфраструктура — 192.168.100.104.",
);

// 4. Термины
const s4 = pres.addSlide();
light(s4);
slideTitle(s4, "Термины — простыми словами", "Чтобы одинаково понимать дальнейшие слайды");
const terms = [
  ["MCP", "Стандартный способ подключить к ИИ внешние инструменты: базу, репозиторий, стенд, браузер."],
  ["Навык", "Инструкция, которую ИИ обязан прочитать до работы: что делать и чего нельзя."],
  ["Субагент", "Отдельная роль ИИ с узкой задачей и своим контролем качества."],
  ["Ledger", "Журнал проверок: что решили проверить, что получилось, что осталось."],
  ["Слой", "Уровень проверок: от простых и быстрых к долгим сквозным сценариям."],
  ["Zephyr", "Система учёта тест-кейсов и результатов, связанная с задачами в Jira."],
];
terms.forEach(([head, text], index) => {
  const col = index % 3;
  const row = Math.floor(index / 3);
  const x = M + col * 4.12;
  const y = 1.8 + row * 2.25;
  card(s4, x, y, 3.85, 2.0);
  s4.addText(head, {
    x: x + 0.3, y: y + 0.24, w: 3.25, h: 0.36, margin: 0,
    fontFace: FONT, fontSize: 17, bold: true, color: BRAND,
  });
  s4.addText(text, {
    x: x + 0.3, y: y + 0.7, w: 3.25, h: 1.15, margin: 0,
    fontFace: FONT, fontSize: 13, color: MUTED, lineSpacing: 18,
  });
});
pageNumber(s4, 4);
s4.addNotes("[~2 мин] Быстрый глоссарий. Если аудитория техническая — пролистать за 30 секунд и идти дальше.");

// 5. Диаграмма: три контура
const s5 = pres.addSlide();
light(s5);
slideTitle(s5, "Как всё связано", "Три контура: источники — управление — продукт; проверяем всё на одном стенде");
nodeBox(s5, M, 2.15, 3.5, 1.9, "Источники кода", "Репозитории сервисов и документация. Только чтение: ожидания не подменяем", {
  fill: CARD, subSize: 11,
});
nodeBox(s5, 4.9, 2.15, 3.5, 1.9, "Управляющий слой", "Правила, инструкции для ИИ, доступы, методология, отчёты", {
  fill: BRAND_SOFT, line: BRAND_LINE, color: BRAND_DARK,
});
nodeBox(s5, 9.2, 2.15, 3.5, 1.9, "Продукт", "Фреймворк автотестов: тесты, данные, учёт кейсов и результатов", {
  fill: CARD,
});
arrow(s5, 4.15, 3.1, 4.85, 3.1);
arrow(s5, 8.45, 3.1, 9.15, 3.1);
nodeBox(s5, 9.2, 4.75, 3.5, 1.5, "Стенд ausn-test1", "Сервисы, база, брокер, административный контур, UI банка", {
  fill: INK, line: INK, color: "FFFFFF", subColor: PANEL_TEXT, subSize: 10.5,
});
doubleArrow(s5, 10.95, 4.15, 10.95, 4.65);
s5.addText("агент читает", {
  x: 4.15, y: 2.72, w: 0.82, h: 0.24, margin: 0, fontFace: FONT, fontSize: 9.5, color: MUTED, align: "center",
});
s5.addText("агент создаёт", {
  x: 8.35, y: 2.72, w: 0.92, h: 0.24, margin: 0, fontFace: FONT, fontSize: 9.5, color: MUTED, align: "center",
});
s5.addText("проверяет", {
  x: 10.4, y: 4.32, w: 1.1, h: 0.24, margin: 0, fontFace: FONT, fontSize: 9.5, color: MUTED, align: "center",
});
pageNumber(s5, 5);
s5.addNotes(
  "[~2 мин] Ключевая мысль: управляющий слой не содержит кода продукта — он описывает, КАК работать, и хранит знания. " +
  "Продукт (тесты) — отдельный репозиторий. Источники кода — только чтение: технически это git pull --ff-only, " +
  "правки и force-push запрещены, чтобы ожидания в тестах не «подгонялись» под удобный результат.",
);

// 6. Что внутри управляющего слоя
const s6 = pres.addSlide();
light(s6);
slideTitle(s6, "Что внутри управляющего слоя", "Пять частей; вместе они делают работу QA повторяемой и переносимой");
const inside = [
  ["Правила", "Границы: что можно менять, где секреты, как разбирать падения"],
  ["Инструкции (навыки)", "11 штук: по контрактам API, категоризации, данным, UI, отчётности"],
  ["Доступы (MCP)", "9 серверов: код, задачи, репозитории, стенды, браузер"],
  ["Методология", "Подходы к тест-дизайну и работе с доказательствами"],
  ["Отчёты", "Разборы, реестры и регламенты — готовые к передаче"],
  ["Переносимость", "Клон на новой машине поднимается по инструкции за минуты"],
];
inside.forEach(([head, text], index) => {
  const col = index % 3;
  const row = Math.floor(index / 3);
  const x = M + col * 4.12;
  const y = 1.75 + row * 2.3;
  card(s6, x, y, 3.85, 2.05);
  badge(s6, x + 0.3, y + 0.3, 0.42, String(index + 1), { fill: index < 3 ? BRAND : "5B9BD5", fontSize: 12 });
  s6.addText(head, {
    x: x + 0.86, y: y + 0.3, w: 2.7, h: 0.4, margin: 0,
    fontFace: FONT, fontSize: 15.5, bold: true, color: INK,
  });
  s6.addText(text, {
    x: x + 0.3, y: y + 0.92, w: 3.25, h: 1.0, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED, lineSpacing: 17,
  });
});
pageNumber(s6, 6);
s6.addNotes(
  "[~2 мин] Технические подробности: skills в .agents/skills, subagents в .opencode/agent, правила в AGENTS.md, " +
  "MCP-конфиги в четырёх файлах (.opencode/opencode.jsonc, .codex/config.toml, .vscode/mcp.json, .mcp.json), " +
  "расхождения ловит tools/checks/mcp_parity.py, методология — docs/qa-methodology, уроки — docs/retrospectives.md (112 записей).",
);

// 7. Диаграмма: MCP-шина
const s7 = pres.addSlide();
light(s7);
slideTitle(s7, "Как агент получает доступ: MCP", "Один стандарт вместо десятка самодельных скриптов; секреты не покидают машину");
nodeBox(s7, M, 2.9, 2.9, 1.5, "ИИ-клиент", "opencode, Codex, VS Code", { fill: CARD, fontSize: 13.5 });
nodeBox(s7, 3.95, 2.9, 2.9, 1.5, "Локальный прокси", "единая точка подключения и входа", { fill: BRAND_SOFT, line: BRAND_LINE, color: BRAND_DARK });
arrow(s7, 3.5, 3.65, 3.9, 3.65);
const servers = [
  "SocratiCode — код и контекст",
  "Atlassian — задачи и требования",
  "GitLab — репозитории и диффы",
  "Стенды — SSH, база, логи, метрики",
  "Playwright, Mattermost — UI и связь",
];
const busX = 7.55;
hline(s7, 6.85, busX, 3.65, { width: 1.5, endArrow: false });
servers.forEach((label, index) => {
  const y = 1.9 + index * 0.78;
  nodeBox(s7, 7.75, y, 4.95, 0.62, label, "", { fill: CARD, fontSize: 12, flat: true });
  hline(s7, busX, 7.72, y + 0.31, { width: 1.25 });
});
vline(s7, busX, 2.21, 5.33, { width: 1.5, endArrow: false });
s7.addText("Шина серверов", {
  x: 6.6, y: 1.52, w: 1.9, h: 0.28, margin: 0, fontFace: FONT, fontSize: 10, color: MUTED, align: "center",
});
pageNumber(s7, 7);
s7.addNotes(
  "[~2 мин] 9 серверов: socraticode, atlassian, gitlab, mattermost, test_ssh, test_pgdb, test_graylog, test_grafana, playwright. " +
  "Прокси — локальный mcp-remote (tools/mcp-runtime, версия зафиксирована); Node читает секреты из корневого .env (--env-file), " +
  "кэш авторизации — .local/mcp-auth. Клиенты запускаются из корня проекта. Один набор — четыре конфигурации, паритет проверяется автоматически.",
);

// 8. MCP по группам
const s8 = pres.addSlide();
light(s8);
slideTitle(s8, "Зачем каждая группа доступа", "Возможности с примерами использования в работе QA");
const groups = [
  ["Код и контекст", "SocratiCode", "Найти, где реализовано поведение; оценить, что затронет правка", BRAND],
  ["Требования", "Atlassian", "Понять задачу и релиз; сверить договорённости с реализацией", "5B9BD5"],
  ["Репозитории", "GitLab", "Посмотреть точную версию файла, изменения и историю", "7030A0"],
  ["Стенды", "SSH · база · логи · метрики", "Проверить контейнеры, состояние данных, причину ошибки в логах", OK],
  ["UI и связь", "Playwright · Mattermost", "Прогнать сценарий в браузере; оповестить команду", WARN],
];
groups.forEach(([head, servers, why, accent], index) => {
  const col = index % 3;
  const row = Math.floor(index / 3);
  const x = M + col * 4.12;
  const y = 1.75 + row * 2.3;
  card(s8, x, y, 3.85, 2.05);
  badge(s8, x + 0.3, y + 0.28, 0.42, String(index + 1), { fill: accent, fontSize: 12 });
  s8.addText(head, {
    x: x + 0.86, y: y + 0.28, w: 2.7, h: 0.38, margin: 0,
    fontFace: FONT, fontSize: 15, bold: true, color: INK,
  });
  s8.addText(servers, {
    x: x + 0.3, y: y + 0.76, w: 3.25, h: 0.34, margin: 0,
    fontFace: FONT, fontSize: 12, bold: true, color: BRAND_DARK,
  });
  s8.addText(why, {
    x: x + 0.3, y: y + 1.14, w: 3.25, h: 0.78, margin: 0,
    fontFace: FONT, fontSize: 12, color: MUTED, lineSpacing: 16,
  });
});
card(s8, M + 8.24, 4.05, 3.85, 2.05, { fill: INK, line: INK });
s8.addText("Правило безопасности", {
  x: M + 8.54, y: 4.28, w: 3.25, h: 0.34, margin: 0,
  fontFace: FONT, fontSize: 14, bold: true, color: "FFFFFF",
});
s8.addText("Доступ — не разрешение менять данные: любые записи только в рамках текущей QA-задачи; секреты хранятся локально.", {
  x: M + 8.54, y: 4.68, w: 3.25, h: 1.2, margin: 0,
  fontFace: FONT, fontSize: 12, color: PANEL_TEXT, lineSpacing: 16,
});
pageNumber(s8, 8);
s8.addNotes(
  "[~2 мин] Детали по серверам: GitLab MCP даёт файл по ref и диффы (на инстансе нет продвинутого поиска по коду — " +
  "поэтому и нужен индекс SocratiCode); test_pgdb — серверы test1-core, test1-categorizer, test1-front-module, " +
  "test1-dbo-integration, test1-admin-backend; test_ssh — vm/ausn-test1, vm/ausn-infra, vm/ausn-test2; " +
  "Graylog — поиск по логам, Grafana — метрики.",
);

// 9. Контекст кода: диаграмма + цифры
const s9 = pres.addSlide();
light(s9);
slideTitle(s9, "Контекст кода: без него ИИ угадывает", "Индекс строится локально: код и данные не уходят наружу");
const flow = [
  ["Репозитории", "15 проектов"],
  ["Индексация", "на своей машине"],
  ["Поиск и анализ", "код, символы, связи"],
  ["Ответ агента", "с опорой на код"],
];
flow.forEach(([head, sub], index) => {
  const x = M + index * 3.15;
  nodeBox(s9, x, 1.8, 2.75, 1.35, head, sub, { fill: index === 1 ? BRAND_SOFT : CARD, line: index === 1 ? BRAND_LINE : LINE, fontSize: 13, subSize: 11 });
  if (index < flow.length - 1) {
    arrow(s9, x + 2.79, 2.47, x + 3.11, 2.47, { width: 1.25 });
  }
});
const stats9 = [
  ["15", "проектов в индексе"],
  ["~8,9 тыс.", "файлов проиндексировано"],
  ["516", "чанков инструкций и ролей"],
];
stats9.forEach(([value, label], index) => {
  const x = M + index * 4.12;
  card(s9, x, 3.5, 3.85, 1.7);
  s9.addText(value, {
    x: x + 0.3, y: 3.68, w: 3.25, h: 0.7, margin: 0,
    fontFace: FONT, fontSize: 34, bold: true, color: BRAND,
  });
  s9.addText(label, {
    x: x + 0.3, y: 4.42, w: 3.25, h: 0.6, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED, lineSpacing: 16,
  });
});
card(s9, M, 5.45, 12.13, 1.35);
s9.addText("Что это меняет: ожидания берём из кода продукта (а не из пересказа), а перед правкой теста видим, что ещё затронуто.", {
  x: M + 0.35, y: 5.66, w: 11.4, h: 0.95, margin: 0,
  fontFace: FONT, fontSize: 13.5, color: INK, valign: "middle",
});
pageNumber(s9, 9);
s9.addNotes(
  "[~2 мин] Технически: SocratiCode + Qdrant (локальный контейнер, порт 17333) + Ollama (nomic-embed-text) — эмбеддинги считаются локально. " +
  "Доступны семантический поиск, символы, трассировка вызовов, граф зависимостей и анализ влияния. " +
  "Инструкции и роли подключены как context artifacts (dot-каталоги индексатор пропускает). Коллекции именуются по пути проекта.",
);

// 10. Навыки
const s10 = pres.addSlide();
light(s10);
slideTitle(s10, "Инструкции для ИИ: 11 навыков", "Каждый навык включается под свою задачу и задаёт границы работы");
const skillRows = [
  ["Процесс и правила", "ausn-qa-loop · ausn-qa-agents · ausn-context-engineering"],
  ["Работа с кодом", "ausn-socraticode · ausn-source-driven-development · karpathy-guidelines"],
  ["Контракты API", "ausn-api-contract-testing"],
  ["Kafka и правила", "ausn-categorizer-lifecycle"],
  ["Данные и документация", "ausn-postman-sync · ausn-qa-methodology · ausn-qa-mcp"],
];
skillRows.forEach(([group, list], index) => {
  const y = 1.75 + index * 0.98;
  card(s10, M, y, 12.13, 0.85);
  s10.addText(group, {
    x: M + 0.3, y: y + 0.24, w: 2.9, h: 0.38, margin: 0,
    fontFace: FONT, fontSize: 14, bold: true, color: INK,
  });
  s10.addText(list, {
    x: M + 3.3, y: y + 0.24, w: 8.5, h: 0.38, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED,
  });
});
pageNumber(s10, 10);
s10.addNotes(
  "[~2 мин] Пример: навык ausn-socraticode требует работать с индексированными проектами только через поиск по коду, " +
  "а ausn-api-contract-testing фиксирует, что ожидания берутся из Pydantic-моделей продукта. Правило: если навык применим — он загружается до первого действия.",
);

// 11. Диаграмма: маршрут субагентов
const s11 = pres.addSlide();
light(s11);
slideTitle(s11, "Роли ИИ: конвейер с обязательной проверкой", "Каждый шаг делает отдельная роль; результат проходит независимое ревью");
const stages = [
  ["Исследование", "источник контракта", CARD, LINE, INK],
  ["Дизайн", "сценарии и данные", CARD, LINE, INK],
  ["Реализация", "тесты и прогон", CARD, LINE, INK],
  ["Ревью", "независимая проверка", BRAND_SOFT, BRAND_LINE, BRAND_DARK],
  ["Готово", "commit и push", OK, OK, "FFFFFF"],
];
stages.forEach(([head, sub, fill, line, color], index) => {
  const x = M + index * 2.48;
  nodeBox(s11, x, 2.2, 2.2, 1.5, head, sub, {
    fill, line, color, fontSize: 14, subSize: 10.5, subColor: color === "FFFFFF" ? "E6F6EC" : MUTED,
  });
  if (index < stages.length - 1) {
    hline(s11, x + 2.2, x + 2.48, 2.95, { width: 1.5 });
  }
});
hline(s11, 5.6, 10.2, 4.35, { color: WARN, width: 1.5, dash: true, beginArrow: true, endArrow: false });
s11.addText("возврат на доработку: замечания ревью должны быть сняты", {
  x: 5.6, y: 4.42, w: 4.6, h: 0.3, margin: 0,
  fontFace: FONT, fontSize: 11, color: MUTED, align: "center",
});
card(s11, M, 5.05, 12.13, 1.55);
s11.addText("Почему это важно", {
  x: M + 0.35, y: 5.24, w: 11.4, h: 0.34, margin: 0,
  fontFace: FONT, fontSize: 15, bold: true, color: INK,
});
s11.addText("Автор не проверяет сам себя: тесты, написанные ИИ, проходят ревью отдельной ролью с правом вернуть работу.", {
  x: M + 0.35, y: 5.62, w: 11.4, h: 0.8, margin: 0,
  fontFace: FONT, fontSize: 12.5, color: MUTED, lineSpacing: 17,
});
pageNumber(s11, 11);
s11.addNotes(
  "[~2 мин] Роли: contract-research-agent → test-design-agent → test-implementation-agent → review-agent; " +
  "дополнительно ci-triage-agent (классификация падений CI) и test-maintenance-agent (flaky и устаревшие тесты), docs-agent (документация). " +
  "Маршрутизация и чекпоинты описаны в навыке ausn-qa-agents; субагенты не коммитят — коммит только после одобрения ревью.",
);

// 12. Sequence: цикл проверки задачи
const s12 = pres.addSlide();
light(s12);
slideTitle(s12, "Цикл проверки задачи: кто с кем говорит", "Диаграмма последовательности (sequence): сплошная стрелка — запрос, пунктир — ответ");
const lives = [
  ["Задача в Jira", 1.7],
  ["Агент", 4.05],
  ["Код продукта", 6.4],
  ["Стенд", 8.75],
  ["Zephyr", 11.1],
];
lives.forEach(([label, cx]) => {
  nodeBox(s12, cx - 1.1, 1.62, 2.2, 0.6, label, "", { fill: INK, line: INK, color: "FFFFFF", fontSize: 12, flat: true });
  vline(s12, cx, 2.32, 6.37, { color: "9AA7BD", width: 1, dash: true, endArrow: false });
});
const messages = [
  [2.72, "Агент", "Задача в Jira", "взять задачу и границы", false],
  [3.32, "Агент", "Код продукта", "источник контракта", false],
  [3.82, "Код продукта", "Агент", "модели и ожидания", true],
  [4.42, "Агент", "Стенд", "прогон проверок", false],
  [4.92, "Стенд", "Агент", "результат с доказательствами", true],
  [5.52, "Агент", "Zephyr", "кейс + привязка + прогон", false],
];
const centerOf = (name) => lives.find(([label]) => label === name)[1];
messages.forEach(([y, from, to, label, dashed]) => {
  const x1 = centerOf(from);
  const x2 = centerOf(to);
  hline(s12, x1, x2, y, {
    color: dashed ? "5B9BD5" : BRAND,
    dash: Boolean(dashed),
    beginArrow: x2 < x1,
    endArrow: x2 > x1,
  });
  const width = Math.abs(x2 - x1) + 1.4;
  s12.addText(label, {
    x: (x1 + x2) / 2 - width / 2, y: y - 0.28, w: width, h: 0.26, margin: 0,
    fontFace: FONT, fontSize: 10.5, color: MUTED, align: "center",
  });
});
card(s12, M, 6.5, 12.13, 0.6, { fill: BRAND_SOFT, line: BRAND_LINE, flat: true });
s12.addText("Сплошная стрелка — запрос, пунктир — ответ. Каждый ответ агент проверяет, а не принимает на веру.", {
  x: M + 0.3, y: 6.62, w: 11.5, h: 0.4, margin: 0,
  fontFace: FONT, fontSize: 12, color: BRAND_DARK, valign: "middle",
});
pageNumber(s12, 12);
s12.addNotes(
  "[~3 мин] Технически: задача берётся из Jira (Atlassian MCP) вместе с релизом; контракт — файлы и модели из репозиториев (GitLab MCP + индекс); " +
  "прогон — pytest по нужному набору, стенд ausn-test1 через SSH/БД/логи; результат фиксируется в Zephyr Scale (кейс, привязка к задаче, прогон). " +
  "Журнал проверок (ledger) — markdown-файл в репозитории продукта со статусами кейсов и provenance-шапкой по задачам.",
);

// 13. Activity: разбор падений
const s13 = pres.addSlide();
light(s13);
slideTitle(s13, "Дисциплина разбора падений", "Диаграмма активности (activity): сначала данные, потом среда, только затем продукт");
s13.addShape(pres.ShapeType.diamond, {
  x: 5.72, y: 1.75, w: 1.9, h: 1.15,
  fill: { color: BRAND_SOFT }, line: { color: BRAND, width: 1.25 }, shadow: undefined,
});
s13.addText("Причина падения?", {
  x: 5.72, y: 1.75, w: 1.9, h: 1.15, margin: 0,
  fontFace: FONT, fontSize: 11, bold: true, color: BRAND_DARK, align: "center", valign: "middle",
});
const branches = [
  ["Данные", "Уникальные данные на прогон; уборка за собой", OK, 1.0],
  ["Окружение", "Skip с причиной и отчёт команде; ложных падений нет", WARN, 4.42],
  ["Продукт", "Дефект с доказательством → фикс → повторная проверка", BRAND, 7.84],
];
vline(s13, 6.67, 2.9, 3.28, { width: 1.25, endArrow: false });
hline(s13, 2.6, 9.44, 3.28, { width: 1.25, endArrow: false });
branches.forEach(([head, text, accent, x]) => {
  vline(s13, x + 1.6, 3.28, 3.53, { width: 1.25 });
  card(s13, x, 3.55, 3.2, 1.5);
  badge(s13, x + 0.26, 3.79, 0.42, "•", { fill: accent, fontSize: 12 });
  s13.addText(head, {
    x: x + 0.8, y: 3.78, w: 2.2, h: 0.34, margin: 0,
    fontFace: FONT, fontSize: 14.5, bold: true, color: INK,
  });
  s13.addText(text, {
    x: x + 0.26, y: 4.24, w: 2.7, h: 0.7, margin: 0,
    fontFace: FONT, fontSize: 11.5, color: MUTED, lineSpacing: 15,
  });
});
card(s13, M, 5.35, 12.13, 1.5, { fill: INK, line: INK });
s13.addText("Полезный эффект", {
  x: M + 0.35, y: 5.54, w: 11.4, h: 0.34, margin: 0,
  fontFace: FONT, fontSize: 15, bold: true, color: "FFFFFF",
});
s13.addText("Красный результат означает проблему продукта, а не «сломанный тест». Ограничения стенда фиксируются отдельно и снимаются после обновления сборки.", {
  x: M + 0.35, y: 5.92, w: 11.4, h: 0.8, margin: 0,
  fontFace: FONT, fontSize: 12.5, color: PANEL_TEXT, lineSpacing: 17,
});
pageNumber(s13, 13);
s13.addNotes(
  "[~2 мин] Технически: причина среды помечается xfail/skip с указанием причины (в декораторах текст латиницей — требование гейта кодировок); " +
  "дефект продукта — xfail(strict=True) со ссылкой на задачу, чтобы при исправлении тест «перевернулся» и потребовал снять маркер. " +
  "Так покрытие не может незаметно устареть.",
);

// 14. Пирамида слоёв
const s14 = pres.addSlide();
light(s14);
slideTitle(s14, "Продукт: пирамида проверок", "Чем ниже слой — тем дешевле и быстрее проверка; чем выше — тем ближе к пользователю");
const pyramid = [
  ["Contract", "эталоны и статические проверки", 7.4],
  ["API", "контракты интерфейсов", 6.4],
  ["DB / Tooling", "данные и админ-инструменты", 5.4],
  ["Integration", "Kafka, категоризация, интеграции", 4.4],
  ["UI / E2E", "сценарии в браузере", 3.4],
];
const cx = 4.3;
pyramid.forEach(([head, sub, width], index) => {
  const y = 6.0 - index * 0.83;
  const x = cx - width / 2;
  const fill = index === 0 ? "E1EDFF" : index === 1 ? "CFE2FF" : index === 2 ? "BBD6FF" : index === 3 ? "A6C9FF" : BRAND;
  card(s14, x, y, width, 0.72, { fill, line: index === 4 ? BRAND : BRAND_LINE, flat: true });
  s14.addText(`${head}  —  ${sub}`, {
    x: x + 0.2, y, w: width - 0.4, h: 0.72, margin: 0,
    fontFace: FONT, fontSize: 12.5, bold: true, color: index === 4 ? "FFFFFF" : INK,
    align: "center", valign: "middle",
  });
});
card(s14, 8.55, 1.75, 4.18, 2.35);
s14.addText("Вне автоматизации", {
  x: 8.85, y: 1.98, w: 3.6, h: 0.34, margin: 0,
  fontFace: FONT, fontSize: 15, bold: true, color: INK,
});
s14.addText("Процессные, инфраструктурные и чисто визуальные проверки. В плане помечены как непройденные — с причиной, а не «покрыто молча».", {
  x: 8.85, y: 2.4, w: 3.6, h: 1.5, margin: 0,
  fontFace: FONT, fontSize: 12.5, color: MUTED, lineSpacing: 17,
});
card(s14, 8.55, 4.3, 4.18, 2.42, { fill: INK, line: INK });
s14.addText("Гейты перед коммитом", {
  x: 8.85, y: 4.52, w: 3.6, h: 0.34, margin: 0,
  fontFace: FONT, fontSize: 15, bold: true, color: "FFFFFF",
});
s14.addText(
  [
    { text: "проверка целостности репозитория — 11 из 11", options: { bullet: true, breakLine: true } },
    { text: "быстрый прогон критических тестов — зелёный/красный", options: { bullet: true, breakLine: true } },
    { text: "контроль кодировок файлов", options: { bullet: true, breakLine: true } },
    { text: "актуальность карты репозитория", options: { bullet: true } },
  ],
  {
    x: 8.85, y: 4.94, w: 3.6, h: 1.6, margin: 0,
    fontFace: FONT, fontSize: 12, color: PANEL_TEXT, paraSpaceAfter: 6,
  },
);
pageNumber(s14, 14);
s14.addNotes(
  "[~2 мин] Технически: слои соответствуют каталогам tests/static+tests/characterization, tests/api, tests/db+tests/tooling, " +
  "tests/kafka+tests/integration, tests/ui. Гейты: scripts/tools/audit_gate.py --full (11/11), scripts/tools/smoke_gate.py, " +
  "scripts/check_text_encoding.py, tools/codemap/generate.py --check.",
);

// 15. Покрытие
const s15 = pres.addSlide();
light(s15);
slideTitle(s15, "Результат: покрытие и трассируемость", "Актуальная автоматизация, а не архив закрытых релизов");
const stats15 = [
  ["381", "тест-кейс в Zephyr"],
  ["521", "связь с 417 задачами"],
  ["41", "версия релизов в аудите"],
];
stats15.forEach(([value, label], index) => {
  const x = M + index * 2.9;
  card(s15, x, 1.75, 2.65, 1.95);
  s15.addText(value, {
    x: x + 0.25, y: 1.95, w: 2.15, h: 0.75, margin: 0,
    fontFace: FONT, fontSize: 36, bold: true, color: BRAND,
  });
  s15.addText(label, {
    x: x + 0.25, y: 2.85, w: 2.15, h: 0.7, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED, lineSpacing: 16,
  });
});
card(s15, 9.45, 1.75, 3.28, 4.72);
s15.addChart(
  pres.ChartType.doughnut,
  [{ name: "Приоритет", labels: ["High (P0/P1)", "Normal (P2)", "Low (P3)"], values: [224, 122, 35] }],
  {
    x: 9.55, y: 2.1, w: 3.08, h: 3.0,
    showTitle: true, title: "Приоритет кейсов", titleFontSize: 13, titleColor: INK,
    showLegend: true, legendPos: "b", legendFontSize: 10, legendColor: MUTED,
    chartColors: [BRAND, "5B9BD5", "A5A5A5"], showValue: false, holeSize: 60,
    dataBorder: { pt: 1, color: "FFFFFF" },
  },
);
card(s15, M, 3.95, 8.55, 2.52);
s15.addText("Что покрыто", {
  x: M + 0.3, y: 4.15, w: 7.9, h: 0.34, margin: 0,
  fontFace: FONT, fontSize: 15, bold: true, color: INK,
});
s15.addText(
  [
    { text: "Правила категоризации: все включённые правила из базы (104) покрыты тестами.", options: { bullet: true, breakLine: true } },
    { text: "Кабинет: сценарии UC-01…UC-25, административный контур, роли банков, отчёты, платежи.", options: { bullet: true, breakLine: true } },
    { text: "Учёт кейсов: 31 функциональный раздел, 8 компонентов продукта.", options: { bullet: true } },
  ],
  {
    x: M + 0.3, y: 4.56, w: 7.9, h: 1.8, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED, paraSpaceAfter: 8,
  },
);
pageNumber(s15, 15);
s15.addNotes(
  "[~2 мин] Числа проверяемы: imported.json (381 кейс), trace_links.json (521 связь / 417 задач), inventory.json (41 версия), " +
  "autotests-ql.csv (224 High / 122 Normal / 35 Low), правило покрытия категоризатора — docs/reports/categorizer-coverage.md. " +
  "Кейсы привязаны к задачам Jira: панель «Покрытие тестирования».",
);

// 16. Стабильность
const s16 = pres.addSlide();
light(s16);
slideTitle(s16, "Результат: наборы зелёные, падений нет", "Прогоны 25.09.2026; пропуски — только с явной причиной");
card(s16, M, 1.75, 12.13, 3.2);
s16.addChart(
  pres.ChartType.bar,
  [
    {
      name: "Пройдено",
      labels: ["API", "Категоризатор", "Contract · DB · Tooling · Unit", "UI/E2E"],
      values: [457, 687, 425, 33],
    },
  ],
  {
    x: M + 0.25, y: 2.0, w: 11.6, h: 2.8,
    barDir: "bar", barGapWidthPct: 60, chartColors: [BRAND],
    showTitle: false, showLegend: false, showValue: true, dataLabelPosition: "outEnd",
    dataLabelFontSize: 12, dataLabelColor: INK, dataLabelFontBold: true,
    catAxisLabelColor: INK, catAxisLabelFontSize: 12,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 11,
    valGridLine: { color: "E6ECF5", size: 1 }, catGridLine: { style: "none" },
    valAxisMaxVal: 750,
  },
);
const notes16 = [
  ["0 падений", "во всех слоях"],
  ["3,2 мин", "быстрый прогон критических тестов"],
  ["Зелёный", "автоматический вердикт"],
];
notes16.forEach(([value, label], index) => {
  const x = M + index * 4.12;
  card(s16, x, 5.15, 3.85, 1.7);
  s16.addText(value, {
    x: x + 0.3, y: 5.34, w: 3.25, h: 0.6, margin: 0,
    fontFace: FONT, fontSize: 25, bold: true, color: OK,
  });
  s16.addText(label, {
    x: x + 0.3, y: 5.98, w: 3.25, h: 0.6, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED, lineSpacing: 16,
  });
});
pageNumber(s16, 16);
s16.addNotes(
  "[~2 мин] Технически: API 457 passed / 0 failed; категоризатор 687 passed (параллельно, -n 8 --dist loadgroup); " +
  "Contract+DB+Tooling+Unit+characterization 425 passed; UI/E2E 33 passed. Часть проверок — xfail с причиной (дрейф сборки стенда, " +
  "внешние контуры). Быстрый гейт: scripts/tools/smoke_gate.py — 273 passed, 18 skipped, 5 xfailed, 191 с.",
);

// 17. Регресс-план
const s17 = pres.addSlide();
light(s17);
slideTitle(s17, "Результат: регресс как управляемая система", "План состоит из прогонов по слоям: Smoke — быстро, Full — полно");
const header = ["Слой", "Smoke (кейсов)", "Full (кейсов)"];
const colX = [M, M + 4.6, M + 7.6];
const colW = [4.4, 2.8, 4.55];
header.forEach((label, index) => {
  s17.addText(label, {
    x: colX[index] + 0.2, y: 1.72, w: colW[index] - 0.4, h: 0.3, margin: 0,
    fontFace: FONT, fontSize: 12, bold: true, color: MUTED,
  });
});
const rows = [
  ["Contract", "5", "5"],
  ["API", "54", "97"],
  ["DB / Tooling", "16", "25"],
  ["Integration", "107", "155"],
  ["UI / E2E", "44", "75"],
];
rows.forEach(([layer, smoke, full], index) => {
  const y = 2.06 + index * 0.62;
  card(s17, M, y, 12.13, 0.54, { flat: index % 2 === 1 });
  s17.addText(layer, {
    x: colX[0] + 0.2, y: y + 0.11, w: colW[0] - 0.4, h: 0.32, margin: 0,
    fontFace: FONT, fontSize: 13, bold: true, color: INK,
  });
  s17.addText(smoke, {
    x: colX[1] + 0.2, y: y + 0.12, w: colW[1] - 0.4, h: 0.3, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED,
  });
  s17.addText(full, {
    x: colX[2] + 0.2, y: y + 0.12, w: colW[2] - 0.4, h: 0.3, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: MUTED,
  });
});
card(s17, M, 5.32, 7.55, 1.55, { fill: INK, line: INK });
s17.addText("Вердикт регресса", {
  x: M + 0.3, y: 5.52, w: 6.95, h: 0.32, margin: 0,
  fontFace: FONT, fontSize: 14, bold: true, color: "FFFFFF",
});
s17.addText("Падений нет в обоих планах; каждый непройденный кейс имеет причину и внесён в остаточные риски.", {
  x: M + 0.3, y: 5.88, w: 6.95, h: 0.9, margin: 0,
  fontFace: FONT, fontSize: 12, color: PANEL_TEXT, lineSpacing: 16,
});
card(s17, 8.35, 5.32, 4.38, 1.55);
s17.addText("Повторный запуск", {
  x: 8.65, y: 5.52, w: 3.8, h: 0.32, margin: 0,
  fontFace: FONT, fontSize: 14, bold: true, color: INK,
});
s17.addText("Добавляет только новые кейсы — план расширяется без дублей.", {
  x: 8.65, y: 5.86, w: 3.8, h: 0.85, margin: 0,
  fontFace: FONT, fontSize: 12, color: MUTED, lineSpacing: 16,
});
pageNumber(s17, 17);
s17.addNotes(
  "[~3 мин] Планы: PKAUSN-P4 «AUSN Регресс 2.0» — 11 прогонов (Smoke+Full по слоям), 525 Pass / 0 Fail / 80 Blocked; " +
  "PKAUSN-P5 «AUSN Smoke (High)» — 5 прогонов, 206 Pass / 0 Fail / 18 Blocked. Технически план в Zephyr состоит из прогонов " +
  "(testPlanKey), состав читается через traceLinks[].testRun; дельта-прогоны добавляют только новые кейсы, --refresh пересоздаёт прогон слоя.",
);

// 18. Находки
const s18 = pres.addSlide();
light(s18);
slideTitle(s18, "Что нашёл управляемый процесс", "Дефекты и дрейфы, подтверждённые прогонами и логами");
const findings = [
  ["Сбой на главном экране", "Ошибка 500 на списке операций в стендовой сборке (в актуальной версии исправлено) — зафиксировано с трассировкой.", BRAND],
  ["Неверный код ответа", "Возвращался 405 вместо 404; после исправления продукта тест «перевернулся» и покрытие стало честным.", OK],
  ["Утечка внутренних данных", "В ответе администратора оставались внутренние адреса ФНС; дефект закрыт и подтверждён повторным прогоном.", OK],
  ["Расхождение сборки стенда", "Роли и статусы отличаются от актуальной версии: отчёт команде и управляемые пропуски вместо ложных падений.", WARN],
];
findings.forEach(([head, text, accent], index) => {
  const y = 1.75 + index * 1.22;
  card(s18, M, y, 12.13, 1.08);
  s18.addShape(pres.ShapeType.ellipse, {
    x: M + 0.32, y: y + 0.32, w: 0.44, h: 0.44,
    fill: { color: accent }, line: { color: accent, width: 1 }, shadow: undefined,
  });
  s18.addText(head, {
    x: M + 1.0, y: y + 0.16, w: 4.1, h: 0.36, margin: 0,
    fontFace: FONT, fontSize: 14.5, bold: true, color: INK,
  });
  s18.addText(text, {
    x: M + 1.0, y: y + 0.54, w: 10.8, h: 0.44, margin: 0,
    fontFace: FONT, fontSize: 12, color: MUTED, lineSpacing: 15,
  });
});
pageNumber(s18, 18);
s18.addNotes(
  "[~2 мин] Технически: NPE OperationMapper.mapRecentOperation (front-module, /api/v1/operation/recent → 500); 405 — снятие маркера xfail " +
  "после фикса; маскирование refusalToAccept — read-side дефект от 02.07, статус переведён в TESTED_PASSING по прогону 25.09. " +
  "Публикации в Jira/Confluence делает человек — управляющий слой готовит текст и доказательства.",
);

// 19. Итоги
const s19 = pres.addSlide();
dark(s19);
s19.addText("Итоги", {
  x: M, y: 0.62, w: 10.0, h: 0.7, margin: 0,
  fontFace: FONT, fontSize: 34, bold: true, color: "FFFFFF",
});
const totals = [
  ["Процесс управляем", "Правила, инструкции и доступы — в одном переносимом репозитории; ИИ работает по инструкциям, а не по памяти."],
  ["Продукт готов", "Фреймворк автотестов по слоям: 381 кейс, падений нет, быстрый и полный регресс."],
  ["Результат проверяем", "521 связь кейсов с 417 задачами: у каждой принятой задачи есть кейс и подтверждённый прогон."],
  ["Знания остаются", "112 уроков сессий, регламенты и отчёты — опыт не уходит вместе с человеком."],
];
totals.forEach(([head, text], index) => {
  const col = index % 2;
  const row = Math.floor(index / 2);
  const x = M + col * 6.15;
  const y = 1.6 + row * 2.05;
  card(s19, x, y, 5.85, 1.82, { fill: PANEL, line: PANEL_LINE, flat: true });
  s19.addText(head, {
    x: x + 0.35, y: y + 0.24, w: 5.15, h: 0.38, margin: 0,
    fontFace: FONT, fontSize: 16.5, bold: true, color: "FFFFFF",
  });
  s19.addText(text, {
    x: x + 0.35, y: y + 0.68, w: 5.15, h: 1.0, margin: 0,
    fontFace: FONT, fontSize: 12.5, color: PANEL_TEXT, lineSpacing: 17,
  });
});
s19.addText("Дальше: визуальные UI-проверки · управляемые триггеры для долгих процессов · подготовка данных · расширение покрытия в CI", {
  x: M, y: 5.95, w: 11.9, h: 0.5, margin: 0,
  fontFace: FONT, fontSize: 13, color: "9FC0FF",
});
s19.addText("Спасибо!  Вопросы — по ходу и после.", {
  x: M, y: 6.55, w: 11.9, h: 0.4, margin: 0,
  fontFace: FONT, fontSize: 13, bold: true, color: "FFFFFF",
});
s19.addNotes(
  "[~2 мин] Финал. Если просят детали: цифры и источники — в docs/presentations/README.md; регламент регресса — " +
  "ausn-qa-project/docs/reports/regression-process.md; навыки — .agents/skills. Вопросы и обсуждение — 5–10 мин.",
);

const output = path.join(__dirname, "ausn-control-plane.pptx");
pres.writeFile({ fileName: output }).then(() => console.log("written:", output));
