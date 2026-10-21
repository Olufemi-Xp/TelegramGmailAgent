import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from app.api.cron import router as cron_router
from app.api.health import router as health_router
from app.api.oauth import router as oauth_router
from app.api.telegram import router as telegram_router
from app.bot.bot import create_bot
from app.config import settings
from app.database.session import engine, init_db
from app.logging_config import get_logger, setup_logging
from app.scheduler.service import scheduler_service

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Personal AI Assistant application...")
    
    # 1. Initialize DB schema
    await init_db()

    # 2. Setup Bot & Polling / Webhook
    bot_task = None
    bot = None
    dp = None
    if settings.TELEGRAM_BOT_TOKEN:
        try:
            bot, dp = create_bot()
            scheduler_service.set_bot(bot)

            if settings.is_webhook_mode:
                logger.info("Operating in Webhook/Serverless mode (Vercel). Continuous polling loop skipped.")
            else:
                await scheduler_service.start()
                # Start Telegram bot polling in background task
                bot_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
                logger.info("Telegram bot polling started successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}", exc_info=True)
    else:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured. Telegram bot initialization skipped.")

    yield

    # Shutdown sequence
    logger.info("Initiating graceful shutdown...")
    await scheduler_service.stop()

    if dp and bot and not settings.is_webhook_mode:
        try:
            await dp.stop_polling()
            await bot.session.close()
            logger.info("Telegram bot polling stopped.")
        except Exception as e:
            logger.warning(f"Error during bot shutdown: {e}")

    if bot_task and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass

    await engine.dispose()
    logger.info("Application shutdown completed.")


app = FastAPI(
    title="Personal AI Assistant API",
    description="Backend API and webhook endpoints for Telegram Personal AI Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(oauth_router)
app.include_router(telegram_router)
app.include_router(cron_router)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("app.main:app", host=settings.HOST, port=port, reload=False)
