Пользователь сделал скриншот. Сохрани и прочитай.

## Шаги

1. Определи ОС и сохрани скриншот из буфера обмена:

**Windows** (Win+Shift+S):
```bash
mkdir -p /c/tmp && powershell.exe -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; if ([System.Windows.Forms.Clipboard]::ContainsImage()) { [System.Windows.Forms.Clipboard]::GetImage().Save('C:/tmp/clipboard_screenshot.png'); Write-Output 'saved' } else { Write-Output 'no image in clipboard' }"
```

**macOS** (Cmd+Shift+4):
```bash
mkdir -p /tmp/claude && pngpaste /tmp/claude/clipboard_screenshot.png 2>/dev/null && echo 'saved' || echo 'no image in clipboard (install: brew install pngpaste)'
```

**Linux** (PrintScreen):
```bash
mkdir -p /tmp/claude && xclip -selection clipboard -t image/png -o > /tmp/claude/clipboard_screenshot.png 2>/dev/null && echo 'saved' || echo 'no image in clipboard (install: apt install xclip)'
```

2. Прочитай сохранённый файл через Read tool
3. Опиши что на скриншоте и спроси что с ним делать
