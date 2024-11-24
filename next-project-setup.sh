# 1. Create new Next.js project
npx create-next-app@latest strategy-framework --typescript --tailwind --eslint --app

# 2. Install required dependencies
cd strategy-framework
npm install @radix-ui/react-alert-dialog @radix-ui/react-tabs lucide-react

# 3. Install shadcn/ui CLI
npx shadcn-ui@latest init

# Choose the following options when prompted:
# - Would you like to use TypeScript? Yes
# - Which style would you like to use? Default
# - Which color would you like to use as base color? Slate
# - Where is your global CSS file? app/globals.css
# - Do you want to use CSS variables? Yes
# - Where is your tailwind.config.js located? tailwind.config.js
# - Configure the import alias for components: @/components
# - Configure the import alias for utils: @/lib/utils

# 4. Add required shadcn/ui components
npx shadcn-ui@latest add button card input textarea tabs alert