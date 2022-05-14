-- Create Product Table
CREATE TABLE IF NOT EXISTS product (
  product_id INT NOT NULL UNIQUE,
  product_name VARCHAR(250) NOT NULL,
  price INT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  PRIMARY KEY (product_id)
)