# 1. Create a new Next.js project with the app directory structure
npx create-next-app@latest strategy-framework --typescript --tailwind --eslint

# 2. Install required dependencies
cd strategy-framework
npm install @radix-ui/react-tabs @radix-ui/react-alert-dialog lucide-react @/components/ui

# 3. Initialize git repository (if not already done by create-next-app)
git init
git add .
git commit -m "Initial commit"

# 4. Install Vercel CLI
npm i -g vercel

# 5. Deploy to Vercel
vercel