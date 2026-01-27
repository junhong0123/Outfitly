---
description: How to run the project with Tailwind CSS
---

# Running Outfitly with Tailwind CSS

## Option 1: Automatic Build (Recommended)
Simply run `dotnet build` or `dotnet run` - Tailwind CSS will compile automatically before each build.

```bash
dotnet run
```

## Option 2: Watch Mode (For Development)
Run Tailwind watch in a **separate terminal** for live CSS updates:

```bash
// turbo
.\tailwindcss.exe -i ./wwwroot/css/output.css -o ./wwwroot/css/site.css --watch
```

Then in another terminal:
```bash
// turbo
dotnet watch run
```

## Option 3: One-time CSS Build
```bash
// turbo
.\tailwindcss.exe -i ./wwwroot/css/output.css -o ./wwwroot/css/site.css --minify
```

## Troubleshooting

### CSS changes not appearing?
1. Rebuild the project with `dotnet build`
2. Clear browser cache (Ctrl+Shift+R)

### Build fails with file locked?
Stop any running Outfitly processes:
```bash
taskkill /F /IM Outfitly.exe
```
