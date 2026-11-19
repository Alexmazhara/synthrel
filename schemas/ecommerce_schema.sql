-- ============================================================================
-- Схема тестовой базы данных: E-Commerce (Электронная коммерция)
-- Разработана для стресс-тестирования СУБД с сохранением ссылочной целостности
-- и проверкой каскадных временных зависимостей.
-- ============================================================================

DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS shipments CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- 1. Пользователи / Покупатели (Корневая таблица жизненного цикла клиента)
CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    country VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, suspended, deleted
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

-- 2. Категории товаров (Справочник)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

-- 3. Товары
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    category_id INT NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    sku VARCHAR(64) NOT NULL UNIQUE,
    base_price NUMERIC(12, 2) NOT NULL CHECK (base_price > 0),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

-- 4. Заказы (Зависит от customers; временная зависимость: order.created_at >= customer.created_at)
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL, -- pending, paid, shipped, delivered, cancelled
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

-- 5. Позиции заказа (Связующая таблица orders <-> products)
CREATE TABLE order_items (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0)
);

-- 6. Платежи (Зависит от orders; временная зависимость: payment_date >= order.created_at)
CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    payment_method VARCHAR(50) NOT NULL, -- credit_card, paypal, crypto, invoice
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    status VARCHAR(50) NOT NULL, -- success, failed, refunded
    payment_date TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

-- 7. Доставка / Отправления (Зависит от orders и payments; shipped_at >= payment_date, delivered_at >= shipped_at)
CREATE TABLE shipments (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    tracking_number VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL, -- prepared, in_transit, delivered, returned
    shipped_at TIMESTAMP WITHOUT TIME ZONE,
    delivered_at TIMESTAMP WITHOUT TIME ZONE
);

-- 8. Отзывы на товары (Зависит от orders, products, customers; created_at >= shipment.delivered_at)
CREATE TABLE reviews (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

-- Индексы для стресс-тестирования производительности (OLTP и аналитические запросы)
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_date ON payments(payment_date);
CREATE INDEX idx_shipments_order_id ON shipments(order_id);
CREATE INDEX idx_reviews_product_id ON reviews(product_id);
