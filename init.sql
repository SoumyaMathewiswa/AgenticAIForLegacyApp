-- Initialize database schema

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    price DECIMAL(10, 2) NOT NULL,
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_price ON products(price);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Shopping carts table
CREATE TABLE IF NOT EXISTS shopping_carts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_carts_user_id ON shopping_carts(user_id);
CREATE UNIQUE INDEX idx_carts_user_product ON shopping_carts(user_id, product_id);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

-- Order items table
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);

-- Seed sample data
INSERT INTO products (name, description, category, price, stock) VALUES
('MacBook Pro 16"', 'High-performance laptop for professionals', 'laptops', 2499.99, 10),
('Dell XPS 15', 'Powerful Windows laptop', 'laptops', 1999.99, 15),
('Lenovo ThinkPad', 'Reliable business laptop', 'laptops', 1299.99, 20),
('iPad Pro 12.9"', 'Versatile tablet for work and creativity', 'tablets', 1099.99, 12),
('Samsung Galaxy Tab S9', 'Premium Android tablet', 'tablets', 799.99, 18),
('AirPods Pro', 'Premium wireless earbuds', 'audio', 249.99, 25),
('Sony WH-1000XM5', 'Industry-leading noise-canceling headphones', 'audio', 399.99, 10),
('Apple Watch Series 9', 'Advanced fitness and health tracker', 'wearables', 399.99, 20),
('Samsung Galaxy Watch 6', 'AMOLED smartwatch with health features', 'wearables', 299.99, 15),
('Magic Keyboard', 'Apple wireless keyboard', 'accessories', 299.99, 30)
ON CONFLICT DO NOTHING;

INSERT INTO users (username, email, full_name) VALUES
('alice', 'alice@example.com', 'Alice Johnson'),
('bob', 'bob@example.com', 'Bob Smith'),
('charlie', 'charlie@example.com', 'Charlie Brown')
ON CONFLICT DO NOTHING;
