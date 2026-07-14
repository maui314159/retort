import { createApp } from './app';

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

const app = createApp();

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Book collection API running on http://localhost:${PORT}`);
  });
}
