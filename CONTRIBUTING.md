# Contributing to cowork-space

이 문서는 팀원이 레포를 처음 설정하고, 변경사항을 공유하는 방법을 설명합니다.

---

## 1. 처음 시작하기

```bash
git clone https://github.com/ko-minseok/cowork-space.git
cd cowork-space
```

Python 의존성 (skill-creator 스크립트용):

```bash
pip install pyyaml
```

Claude Code on the web을 사용하는 경우 세션 시작 시 자동으로 설치됩니다.

---

## 2. 최신 상태 유지

**작업 시작 전 항상 pull합니다.**

```bash
git pull --ff-only origin main
```

wiki나 skill이 충돌하면 아래 [충돌 해결](#충돌-해결) 섹션을 참고하세요.

---

## 3. 브랜치 전략

| 작업 | 브랜치 |
|------|--------|
| Skill 추가/수정 | `feat/skill-<name>` |
| Wiki 대규모 ingest | `wiki/<topic>` |
| 버그 수정 | `fix/<description>` |
| 일상적인 wiki 편집 | `main` 직접 커밋 허용 |

일상적인 wiki ingest (소규모)는 `main`에 직접 push해도 됩니다.
`.claude/commands/`나 `scripts/` 변경은 반드시 PR을 통해 리뷰 후 merge합니다.

---

## 4. Wiki 작업 흐름

### 새 소스 추가

```bash
# 1. 최신 상태 확인
git pull --ff-only origin main

# 2. 소스 ingest (Claude Code 세션에서)
/wiki:ingest sources/my-paper.pdf
# 또는 스크립트 직접 실행
python scripts/wiki/ingest.py sources/my-paper.pdf

# 3. 변경된 wiki 파일 커밋
git add wiki/ sources/
git commit -m "wiki: ingest my-paper.pdf"
git push origin main
```

### 질문하기

```bash
/wiki:query RLHF란 무엇인가?
```

답변을 저장하려면:

```bash
/wiki:query --file-answer RLHF란 무엇인가?
```

### Wiki 상태 점검

```bash
python scripts/wiki/lint.py
```

---

## 5. Skill 추가

새 slash command를 만들려면:

```bash
/skill-creator
```

또는 직접 작성:

1. `.claude/commands/<group>/<name>.md` 파일 생성
2. 유효성 검사: `python scripts/skill-creator/quick_validate.py .claude/commands/<skill-dir>`
3. PR 제출 → 리뷰 → merge

---

## 6. 커밋 컨벤션

```
feat:     새 기능 또는 skill
fix:      버그 수정
wiki:     wiki 페이지 추가/수정
chore:    설정, 의존성, 스크립트 변경
docs:     문서 (README, CONTRIBUTING 등)
refactor: 기능 변경 없는 코드 정리
```

예시:
```
wiki: ingest attention-is-all-you-need.pdf
feat: add /dev:deploy skill
fix: handle empty query in query.py
```

---

## 7. 충돌 해결

### Wiki 충돌 (`wiki/*.md`)

두 명이 같은 페이지를 동시에 수정했을 때:

```bash
git pull --ff-only origin main  # 실패하면 아래 방법 사용
git fetch origin
git merge origin/main
# 충돌 파일 확인
git status
```

충돌 부분을 열어 두 변경사항을 모두 보존합니다.
wiki의 contradiction policy에 따라 두 내용을 병합하거나 `> ⚠️ Contradiction:` 블록으로 표시합니다.

### Skill 충돌 (`.claude/commands/`)

Skill 파일 충돌은 드물지만, 발생하면 PR을 통해 팀이 리뷰합니다.

---

## 8. Session-start Hook

Claude Code on the web 세션이 시작될 때 자동으로:
1. `git pull` — 최신 변경사항 동기화
2. `python3 -c "import yaml"` — 의존성 확인
3. `python scripts/wiki/lint.py` — wiki 상태 점검

결과는 세션 시작 로그에서 확인할 수 있습니다.

로컬에서 hook을 직접 실행하려면:

```bash
CLAUDE_CODE_REMOTE=true CLAUDE_PROJECT_DIR=$(pwd) .claude/hooks/session-start.sh
```

---

## 9. 도움말

사용 가능한 slash command 전체 목록:

```
/help
```

개발 철학 및 Wiki 스키마:

- `CLAUDE.md` — 전체 가이드
- `wiki/schema.md` — 페이지 작성 규칙
