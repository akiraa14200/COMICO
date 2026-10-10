#!/usr/bin/env python3
"""Apply COMICO's UI-only rebrand to the source archive before building.

Internal package names and third-party license notices are intentionally preserved.
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


# Remove Support Us and Help from the More screen.
rel = "app/src/main/java/eu/kanade/presentation/more/MoreScreen.kt"
path, text = read(rel)
before = text
for token in ("MR.strings.label_support_us", "MR.strings.label_help"):
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

# Remove the Support Us navigation callback.
rel = "app/src/main/java/eu/kanade/tachiyomi/ui/more/MoreTab.kt"
path, text = read(rel)
before = text
text = text.replace("import mihon.feature.support.SupportUsScreen\n", "")
text = text.replace("            onClickSupport = { navigator.push(SupportUsScreen()) },\n", "")
write_if_changed(path, before, text, "Removed Support Us navigation callback")

# Remove the startup donation campaign so it no longer appears as a prompt.
rel = "app/src/main/java/eu/kanade/tachiyomi/ui/main/MainActivity.kt"
path, text = read(rel)
before = text
text = "\n".join(line for line in text.split("\n") if line.strip() != "ShowDonationCampaign()")
text, _ = remove_function(text, "private fun ShowDonationCampaign()")
text = text.replace("import mihon.feature.support.SupportUsScreen\n", "")
write_if_changed(path, before, text, "Removed startup Support Us campaign")

# Rebrand About and remove old Mihon website/social destinations.
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
if old_logo not in text:
    raise SystemExit("Could not locate About screen brand header")
text = text.replace(old_logo, new_brand, 1)
text, privacy_removed = remove_item_with_token(text, "MR.strings.privacy_policy")
text, links_removed = remove_item_with_token(text, "LinkIcon(")
if not privacy_removed or not links_removed:
    raise SystemExit("Could not safely remove legacy About links")
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

# Remove the Getting Started guide if it is a standalone onboarding list item.
guide_rel = "app/src/main/java/eu/kanade/tachiyomi/ui/more/OnboardingScreen.kt"
guide_path = root / guide_rel
if guide_path.exists():
    guide_before = guide_path.read_text(encoding="utf-8")
    guide_after, guide_removed = remove_item_with_token(guide_before, "onboarding_guides_new_user")
    if guide_removed:
        guide_after, _ = remove_item_with_token(guide_after, "onboarding_guides_returning_user")
        write_if_changed(guide_path, guide_before, guide_after, "Removed Getting Started guide onboarding item")

# Apply a shared translucent glass-like surface treatment through the app-wide Compose theme.
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
if old_theme not in text:
    raise SystemExit("Could not locate shared theme block for glassmorphic styling")
text = text.replace(old_theme, new_theme, 1)
write_if_changed(path, before, text, "Added shared glassmorphic theme treatment")

# Update only an explicit app display-name string; leave internal namespaces and license notices intact.
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
if len(changes) < 4:
    raise SystemExit("Too few source changes were applied; refusing to build/commit.")
