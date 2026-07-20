# Existing Repo Update Notes — PS_2

This package is configured to update the existing GitHub repository:

```text
https://github.com/dansamuka/PS_2.git
```

The deployment approach is: **update the existing repo**, not create a fresh repo.

## What the push script does

`PUSH_TO_GITHUB.cmd`:

1. validates `data/public_sector_feed.json` against `data/source_registry.json`;
2. clones the existing `PS_2` repo into a temporary folder;
3. overlays the current package into that clone;
4. commits only if files changed;
5. pushes back to `main`.

It does **not** run `gh repo create`.

## Run command

```bat
PUSH_TO_GITHUB.cmd
```

Default target:

```text
https://github.com/dansamuka/PS_2.git
```

Default Pages URL:

```text
https://dansamuka.github.io/PS_2/
```

Default raw feed URL:

```text
https://raw.githubusercontent.com/dansamuka/PS_2/main/data/public_sector_feed.json
```

## Phase 1 stabilisation changes

- `PS_2` is treated as the canonical deployment repo.
- County source coverage has been removed.
- All national/government-related role families remain visible.
- `View original role` links are mandatory.
- `VERIFY_PHASE_1.cmd` has been added for local validation.

## Public/private warning

The screenshot shows `PS_2` is public. Keep the repo limited to public vacancy records only. Do not put CVs, private notes, application decisions, personal phone numbers, or sensitive reviewer comments into the public repo.
