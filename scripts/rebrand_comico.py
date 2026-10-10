#!/usr/bin/env python3
"""Apply COMICO's UI-only rebrand to the source archive before building.

Internal package names and third-party license notices are intentionally preserved.
This patch is idempotent so repeated builds are safe.
"""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "source/mihon-main")
changes = []


def read(rel):
    path = root / rel
    if not path.exists():
        raise SystemExit(f"Required source file missing: {rel}")
    return path, path.read_text(encoding="utf-8")


def write_if_changed(path, before, after, label):
    if before != after:
        path.write_text(after, encoding="utf-8")
        changes.append(label)


def remove_item_with_token(text, token):
    lines = text.splitlines(keepends=True)
    index = next((i for i, line in enumerate(lines) if token in line), None)
    if index is None:
        return text, False
    start = next(
        (i for i in range(index, -1, -1) if re.match(r"\s*item\s*\{\s*$", lines[i])),
        None,
    )
    if start is None:
        return text, False
    depth = 0
    opened = False
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if "{" in lines[i]:
            opened = True
        if opened and depth == 0:
            del lines[start : i + 1]
            return "".join(lines), True
    return text, False


def remove_function(text, signature):
    lines = text.splitlines(keepends=True)
    index = next((i for i, line in enumerate(lines) if signature in line), None)
    if index is None:
        return text, False
    start = index
    while start > 0 and lines[start - 1].strip() == "":
        start -= 1
    if start > 0 and lines[start - 1].strip() == "@Composable":
        start -= 1
    depth = 0
    opened = False
    for i in range(index, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if "{" in lines[i]:
            opened = True
        if opened and depth == 0:
            end = i + 1
            while end < len(lines) and lines[end].strip() == "":
                end += 1
            del lines[start:end]
            return "".join(lines), True
    return text, False


# More menu: remove Support Us and Help.
rel = "app/src/main/java/eu/kanade/presentation/more/MoreScreen.kt"
path, text = read(rel)
before = text
for token in ("MR.strings.label_support_us", "MR.strings.label_help"):
    if token in text:
        text, ok = remove_item_with_token(text, token)
        if not ok:
            raise SystemExit(f"Could not safely remove {token} from {rel}")
text = text.replace("    onClickSupport: () -> Unit,\n", "")
for line in (
    "import androidx.compose.material.icons.automirrored.outlined.HelpOutline\n",
    "import androidx.compose.material.icons.filled.VolunteerActivism\n",
    "import tachiyomi.core.common.Constants\n",
    "import androidx.compose.ui.platform.LocalUriHandler\n",
    "    val uriHandler = LocalUriHandler.current\n\n",
):
    text = text.replace(line, "")
write_if_changed(path, before, text, "Removed Support Us and Help entries from More screen")

# Remove Support Us navigation.
rel = "app/src/main/java/eu/kanade/tachiyomi/ui/more/MoreTab.kt"
path, text = read(rel)
before = text
text = text.replace("import mihon.feature.support.SupportUsScreen\n", "")
text = text.replace("            onClickSupport = { navigator.push(SupportUsScreen()) },\n", "")
write_if_changed(path, before, text, "Removed Support Us navigation callback")

# Remove the startup donation campaign.
rel = "app/src/main/java/eu/kanade/tachiyomi/ui/main/MainActivity.kt"
path, text = read(rel)
before = text
text = "\n".join(line for line in text.split("\n") if line.strip() != "ShowDonationCampaign()")
text, _ = remove_function(text, "private fun ShowDonationCampaign()")
text = text.replace("import mihon.feature.support.SupportUsScreen\n", "")
write_if_changed(path, before, text, "Removed startup Support Us campaign")

# COMICO About branding; remove Mihon-specific privacy and social destinations.
rel = "app/src/main/java/eu/kanade/presentation/more/settings/screen/about/AboutScreen.kt"
path, text = read(rel)
before = text
old_logo = """                item {
                    LogoHeader(
                        iconPadding = PaddingValues(vertical = 56.dp),
                    )
                }"""
new_brand = """                item {
                    TextPreferenceWidget(
                        title = "COMICO",
                        subtitle = "Brand",
                    )
                }"""
if old_logo in text:
    text = text.replace(old_logo, new_brand, 1)
elif 'title = "COMICO"' not in text:
    raise SystemExit("Could not locate About screen brand header")
for token in ("MR.strings.privacy_policy", "LinkIcon("):
    if token in text:
        text, ok = remove_item_with_token(text, token)
        if not ok:
            raise SystemExit(f"Could not safely remove legacy About entry: {token}")
for line in (
    "import eu.kanade.presentation.more.LogoHeader\n",
    "import tachiyomi.core.common.Constants\n",
    "import tachiyomi.presentation.core.components.LinkIcon\n",
    "import tachiyomi.presentation.core.icons.CustomIcons\n",
    "import tachiyomi.presentation.core.icons.Discord\n",
    "import tachiyomi.presentation.core.icons.Facebook\n",
    "import tachiyomi.presentation.core.icons.Github\n",
    "import tachiyomi.presentation.core.icons.Reddit\n",
    "import tachiyomi.presentation.core.icons.X\n",
):
    text = text.replace(line, "")
write_if_changed(path, before, text, "Rebranded About screen as COMICO and removed Mihon links")

# Remove a standalone onboarding guide item if present.
guide_path = root / "app/src/main/java/eu/kanade/tachiyomi/ui/more/OnboardingScreen.kt"
if guide_path.exists():
    guide_before = guide_path.read_text(encoding="utf-8")
    guide_after = guide_before
    for token in ("onboarding_guides_new_user", "onboarding_guides_returning_user"):
        if token in guide_after:
            guide_after, _ = remove_item_with_token(guide_after, token)
    write_if_changed(guide_path, guide_before, guide_after, "Removed Getting Started guide onboarding item")

# Remove the Getting Started guide panel from onboarding while preserving backup restore.
rel = "app/src/main/java/eu/kanade/presentation/more/onboarding/GuidesStep.kt"
path, text = read(rel)
before = text
guide_block = """            Text(stringResource(MR.strings.onboarding_guides_new_user, stringResource(MR.strings.app_name)))
            Button(
                modifier = Modifier.fillMaxWidth(),
                onClick = { handler.openUri(GETTING_STARTED_URL) },
            ) {
                Text(stringResource(MR.strings.getting_started_guide))
            }

            HorizontalDivider(
                modifier = Modifier.padding(vertical = 8.dp),
                color = MaterialTheme.colorScheme.onPrimaryContainer,
            )

"""
if guide_block in text:
    text = text.replace(guide_block, "", 1)
text = text.replace("import androidx.compose.material3.HorizontalDivider\\n", "")
text = text.replace("import androidx.compose.ui.platform.LocalUriHandler\\n", "")
text = text.replace("        val handler = LocalUriHandler.current\\n\\n", "")
text = text.replace('const val GETTING_STARTED_URL = "https://mihon.app/docs/guides/getting-started"\\n', "")
write_if_changed(path, before, text, "Removed Getting Started guide panel from onboarding")

# Shared app-wide translucent/glass-like Compose theme.
rel = "app/src/main/java/eu/kanade/presentation/theme/TachiyomiTheme.kt"
path, text = read(rel)
before = text
imports = [
    "import androidx.compose.foundation.background",
    "import androidx.compose.foundation.layout.Box",
    "import androidx.compose.foundation.layout.fillMaxSize",
    "import androidx.compose.ui.graphics.Brush",
]
anchor = "import androidx.compose.foundation.isSystemInDarkTheme"
for imp in imports:
    if imp not in text:
        if anchor not in text:
            raise SystemExit(f"Could not add theme import: {imp}")
        text = text.replace(anchor, anchor + "\n" + imp, 1)
old_theme = """    MaterialExpressiveTheme(
        colorScheme = remember(appTheme, isDark, isAmoled) {
            getThemeColorScheme(
                context = context,
                appTheme = appTheme,
                isDark = isDark,
                isAmoled = isAmoled,
            )
        },
        content = content,
    )"""
new_theme = """    val baseColorScheme = remember(appTheme, isDark, isAmoled) {
        getThemeColorScheme(
            context = context,
            appTheme = appTheme,
            isDark = isDark,
            isAmoled = isAmoled,
        )
    }
    val glassColorScheme = remember(baseColorScheme) {
        baseColorScheme.copy(
            surface = baseColorScheme.surface.copy(alpha = 0.92f),
            surfaceContainerLowest = baseColorScheme.surfaceContainerLowest.copy(alpha = 0.58f),
            surfaceContainerLow = baseColorScheme.surfaceContainerLow.copy(alpha = 0.66f),
            surfaceContainer = baseColorScheme.surfaceContainer.copy(alpha = 0.74f),
            surfaceContainerHigh = baseColorScheme.surfaceContainerHigh.copy(alpha = 0.80f),
            surfaceContainerHighest = baseColorScheme.surfaceContainerHighest.copy(alpha = 0.86f),
            outlineVariant = baseColorScheme.outlineVariant.copy(alpha = 0.46f),
        )
    }
    MaterialExpressiveTheme(colorScheme = glassColorScheme) {
        Box(
            modifier = androidx.compose.ui.Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            baseColorScheme.background,
                            baseColorScheme.surface.copy(alpha = 0.42f),
                            baseColorScheme.background,
                        ),
                    ),
                ),
        ) {
            content()
        }
    }"""
if old_theme in text:
    text = text.replace(old_theme, new_theme, 1)
elif "val glassColorScheme = remember(baseColorScheme)" not in text:
    raise SystemExit("Could not locate shared theme block for glassmorphic styling")
write_if_changed(path, before, text, "Added shared glassmorphic theme treatment")

# Change only explicit Android app-name strings, not packages or license notices.
for path in (root / "app/src/main/res").rglob("strings.xml"):
    before = path.read_text(encoding="utf-8", errors="ignore")
    after = re.sub(
        r'(<string\s+name="app_name"[^>]*>)\s*Mihon\s*(</string>)',
        r'\1COMICO\2',
        before,
        flags=re.I,
    )
    write_if_changed(path, before, after, f"Updated app display name in {path.relative_to(root)}")

print("COMICO source modifications:")
for change in changes:
    print(f"- {change}")
if not changes:
    print("Source already has the COMICO patch; no changes needed.")
