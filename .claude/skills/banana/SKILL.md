Пользователь просит сгенерировать изображение через "банану" / "Nano Banana".

## Что делать

Использовать Google Gemini Pro Image (последнюю Pro-версию модели Nano Banana) для генерации изображений.

### Найти актуальную модель

```python
from google import genai
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
for m in client.models.list():
    if 'image' in m.name.lower() and 'pro' in m.name.lower():
        print(m.name)
```

На март 2026: `gemini-3-pro-image-preview`

### Генерация

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",  # обновить если появится новее
    contents=prompt,
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
    ),
)

for part in response.candidates[0].content.parts:
    if part.inline_data and part.inline_data.mime_type.startswith("image/"):
        Path("output.png").write_bytes(part.inline_data.data)
        break
```

### Референсы

Можно прикладывать изображения как reference вместе с промптом:

```python
from PIL import Image

ref_image = Image.open("reference.png")

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[ref_image, prompt_text],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
    ),
)
```

### API ключ

`GOOGLE_API_KEY` из `.env` в корне проекта.

### Пакеты

`google-genai` (уже установлен в cortex).
