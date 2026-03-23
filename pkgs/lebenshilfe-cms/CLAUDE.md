# Django CMS Development Context

This repository contains the `lebenshilfe-cms` Django application. Assume all terminal commands and scripts are executed within a pre-configured `nix develop` environment. 

## 🛠 Tech Stack
- **Core Framework**: Django (Python 3.13)
- **Admin Theme**: Django-Unfold
- **Version Control**: Jujutsu (`jj`)

## 📂 App Structure
- `base`: Core models and mixins (Persons, Phones, Addresses, etc.)
- `finance`: Financial data models (FeeAgreements, Payers, Payments)
- `hr`: Human resources models (Employees, Salary, Absences)
- `members`: Membership management
- `pedagogy`: Pedagogical tracking (Students, Supervisions, Requests)
- `lebenshilfe`: Main project configuration (settings, urls, asgi, wsgi)

## 📜 Core Rules & Workflows

### 1. Version Control (Jujutsu) - AUTOMATIC COMMITS REQUIRED
- **DO NOT** use standard `git` commands (no `git add`, `git commit`, `git checkout`).
- **DO** use Jujutsu (`jj`) commands (`jj status`, `jj diff`, `jj new`, `jj describe`).
- **Mandatory Auto-Commits**: You must actively and automatically create `jj` commits for your changes with **meaningful granularity**. Do not bundle unrelated changes. 
  - *Example:* Create one commit for a model change + migration, and a separate commit for the corresponding UI/Admin changes.
- **Commit Messages**: Use Conventional Commits formatting via `jj describe -m "<type>(<scope>): <summary>"`.
  - Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.

### 2. Language & Localization
- **User-Facing UI (German)**: Everything the user sees in the Django Admin (`verbose_name`, `help_text`, template strings, messages) must be in **German**.
- **Internal Code (English)**: Variables, function names, class names, database columns, and code comments must be in **English**.

### 3. Environment & Dependencies
- You are operating inside a `nix develop` shell.
- **DO NOT** suggest creating virtual environments (`python -m venv`) or running `pip install`. 
- If a new Python dependency is required, add it to `pyproject.toml` and inform the user so they can update their Nix configuration.

### 4. Django Development Guidelines & Testing
- All Django commands must be executed from the `pkgs/lebenshilfe-cms/` directory.
- **Mandatory Testing**: Before finalizing changes, verify that the code works:
  - **Migrations**: Always generate and apply migrations (`python manage.py makemigrations` and `python manage.py migrate`) when modifying `models.py`. Include the generated migration files in your `jj` commit.
  - **Runserver**: Run `python manage.py runserver` to ensure the application starts correctly and the Django Admin loads without crashes or syntax errors.
- **Django Admin & Unfold Integration**: 
  - Subclass `BaseModelAdmin` from `base.admin` instead of default Django or Unfold ModelAdmins. It already integrates `unfold.admin.ModelAdmin` along with necessary custom mixins (`EditModeMixin`, `CustomWidgetsMixin`, `AdminDisplayMixin`).
  - For generic tabular inlines, subclass `BaseGenericTabularInline` from `base.admin`.
- **Best Practices**:
  - Output clean, modern Python 3.13 code using type hints.
  - Follow the "fat models, thin views" principle.
  - Heavily optimize queries using `select_related` and `prefetch_related` in `admin.py` and `views.py`.

### 5. Code Modification Rules
- Do not remove or overwrite existing unrelated code, comments, or imports when making edits.
- Provide targeted diffs or clear, fully functioning file replacements when making larger changes.
