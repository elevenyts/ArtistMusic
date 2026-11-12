# 🌍 Localization System

This system handles multi-language support for the bot using YAML files and Go's `embed` package.

## 📂 Project Structure
* `kanha/locales/*.yml`: Language translation files.
* `kanha/locales/loader.go`: Core logic for loading and fetching strings.
* `kanha/modules/helpers.go`: Contains `F()` and `FWithLang()` for easy access.

## 🛠️ How to Add a New Language
1. **Create File:** Create `kanha/locales/{code}.yml` (e.g., `es.yml`).
2. **Define Name:** Set the display name: `name: "🇪🇸 Español"`.
3. **Translate:** Copy keys from `en.yml` and translate. 
   * Use `{key}` for variables (e.g., `Hello {user}`).
   * Use `|` for multi-line strings.
4. **Deploy:** Files are automatically embedded; no code changes are required.

## 📝 Usage for Developers
Use these helpers instead of calling the loader directly:
* `F(chatID, key, args...)`: Automatically detects chat language.
* `FWithLang(lang, key, args...)`: Force a specific language.

---

## 👥 Language Contributors

| Language | Code | Contributor |
| :--- | :--- | :--- |
| 🇺🇸 English | `en` | [@Oyekanhaa](https://github.com/Oyekanhaa) |
| 🇮🇳 Hindi | `hi` | [@Oyekanhaa](https://github.com/Oyekanhaa) |
| 🇸🇦 Arabic | `ar` | [@Oyekanhaa](https://github.com/Oyekanhaa) |
| 🇹🇷 Turkish | `tr` | [@Oyekanhaa](https://github.com/Oyekanhaa) |
---
*All YAML files in `kanha/locales/` are automatically embedded into the binary during compilation.*