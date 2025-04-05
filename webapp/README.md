# Notion Triage Web

This is the web version of Notion Triage, built with Next.js and designed to be deployed on Vercel. It provides a modern web interface for the Notion Triage task management system.

## Features

- Modern, responsive web interface
- Integration with Notion API
- Google Calendar integration
- Task management and scheduling
- Real-time updates
- Beautiful UI with Tailwind CSS

## Getting Started

### Prerequisites

- Node.js 18.x or later
- Notion API key
- Google Calendar API credentials
- Vercel account (for deployment)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd notiontriage/webapp
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env.local` file in the webapp directory with the following variables:
```
NOTION_API_KEY=your_notion_api_key
DATABASE_ID=your_notion_database_id
```

4. Run the development server:
```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Deployment

This application is designed to be deployed on Vercel. To deploy:

1. Push your code to a Git repository
2. Connect your repository to Vercel
3. Add your environment variables in the Vercel dashboard
4. Deploy!

## Project Structure

- `src/app`: Next.js app router pages and layouts
- `src/components`: Reusable React components
- `src/lib`: Utility functions and API clients
- `src/types`: TypeScript type definitions
- `src/styles`: Global styles and Tailwind configuration

## Development

- `npm run dev`: Start development server
- `npm run build`: Build for production
- `npm run start`: Start production server
- `npm run lint`: Run ESLint

## License

[Add your license information here] 