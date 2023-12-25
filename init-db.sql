CREATE TABLE trade_data (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    token VARCHAR(32),
    order_id VARCHAR(36),
    position_size NUMERIC,
    side VARCHAR(4),
    order_type VARCHAR(32),
    price NUMERIC
);

CREATE FUNCTION notify_new_trade()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('new_trade_channel', row_to_json(NEW)::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_notify_new_trade
AFTER INSERT ON trade_data
FOR EACH ROW EXECUTE FUNCTION notify_new_trade();
