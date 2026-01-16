# GitHub Push Instructions

## Step 1: Create Repository on GitHub

Go to https://github.com/new and create a new repository:

**Settings:**
- Repository name: `holistic-urban-simulator`
- Description: `Multi-city urban policy analysis simulator for Berlin, Leipzig, and Munich. Tests policy scenarios with interactive dashboards.`
- Visibility: **Public** (recommended for portfolio) or Private
- Do NOT initialize with README, .gitignore, or license (we already have these locally)
- Click "Create repository"

## Step 2: After Creating the Repo

You'll see the push instructions. Use one of these commands (replace YOUR_USERNAME):

### Option A: HTTPS (Easier if you don't have SSH set up)
```bash
cd "c:\Users\sivan\OneDrive\Documents\Rag projects\urban Simulator\holistic_urban_simulator"
git remote add origin https://github.com/YOUR_USERNAME/holistic-urban-simulator.git
git branch -M main
git push -u origin main
```

### Option B: SSH (More secure, requires SSH key)
```bash
cd "c:\Users\sivan\OneDrive\Documents\Rag projects\urban Simulator\holistic_urban_simulator"
git remote add origin git@github.com:YOUR_USERNAME/holistic-urban-simulator.git
git branch -M main
git push -u origin main
```

## Step 3: Verify on GitHub

After pushing, refresh https://github.com/YOUR_USERNAME/holistic-urban-simulator and verify all files appear.

---

## Quick Copy-Paste Version (HTTPS)

Replace `YOUR_USERNAME` and `YOUR_GITHUB_TOKEN` then run:

```bash
git remote add origin https://YOUR_USERNAME:YOUR_GITHUB_TOKEN@github.com/YOUR_USERNAME/holistic-urban-simulator.git
git branch -M main
git push -u origin main
```

Or simpler (will prompt for password):
```bash
git remote add origin https://github.com/YOUR_USERNAME/holistic-urban-simulator.git
git branch -M main
git push -u origin main
```

---

**Note**: If you get authentication errors, you may need to:
1. Use a Personal Access Token instead of password (HTTPS)
2. Set up SSH keys (SSH)
