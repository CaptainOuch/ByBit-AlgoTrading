# ByBit Algo-Trading Bot

## Description

At the start, the bot checks for an active order on the token. If there is one, it outputs an error in the terminal indicating that this token was previously launched not by the bot. If there is no active order, it enters a long position. The robot monitors PnL (profit and loss). If PnL falls by -5%, the bot places a limit order at the current price. If a sell order is already placed and PnL falls to -8%, the previous sell order is cancelled and a new one is placed at the market price. If the price rises by 5%, the robot moves the stop-loss line up by 1%. If the PnL price rises by 10%, the stop-loss is moved up by 5% of PnL.

- **Multiple Tokens Support**: Trade multiple tokens simultaneously.
- **Telegram Logging**: All trading logs are sent to a specified Telegram channel.

## Setup

1. Create a `.env` file in the project's root directory and fill in the environment variables according to `.env.example`.
2. Obtain Telegram API keys at [https://my.telegram.org/](https://my.telegram.org/).
3. Get your Telegram channel ID via [https://t.me/username_to_id_bot](https://t.me/username_to_id_bot).
4. Obtain ByBit API keys from the official ByBit website - [https://www.bybit.com/](https://www.bybit.com/), or from the ByBit test version - [https://testnet.bybit.com/](https://testnet.bybit.com/).

## Launch

docker-compose up


## Описание

На старте, бот проверяет нет ли активного ордера по токену. Если да, то выдает ошибку в терминал, что этот токен был запущен ранее НЕ ботом. Если нет – заходит в лонг позицию. Робот отслеживает pnl. Если pnl упал на -5 процентов, бот выставляет лимитный ордер по актуальной цене. Если ордер на продажу уже стоит, а pnl упал до -8%, то предыдущий ордер на продажу отменяется и выставляется новый по рынку. Если цена выросла на 5 процентов, робот перемещает линию по стоп-лосу на 1%. Если цена pnl выросла на 10%, стоп-лосс перемещается на 5% pnl.

- **Поддержка нескольких токенов**: Можно торговать сразу несколькими токенами.
- **Логирование в Telegram**: Все логи торгов отправляются в указанный Telegram-канал.

## Настройка

1. Создайте файл `.env` в корневом каталоге проекта и заполните переменные окружения в соответствии с `.env.example`.
2. Получите API-ключи для Telegram, на https://my.telegram.org/.
3. Получите ID вашего Telegram-канала через https://t.me/username_to_id_bot.
4. Получите API-ключи для ByBit на официальном сайте ByBit - https://www.bybit.com/. Либо на тестовой версии BytBit - https://testnet.bybit.com/

## Запуск

docker-compose up


