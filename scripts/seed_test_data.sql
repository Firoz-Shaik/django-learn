-- GreatKart test seed (PostgreSQL)
-- Login with EMAIL + password: user@123
-- Images are empty strings; add files in admin later.
-- Safe to re-run: existing IDs are skipped (ON CONFLICT DO NOTHING).
--   psql -U postgres -d greatkart -f scripts/seed_test_data.sql

BEGIN;

-- Same Django 6.1 PBKDF2 hash for user@123
-- pbkdf2_sha256$1500000$...
-- Users 101-105 (existing accounts use ids 2 and 14)

INSERT INTO accounts_account (
    id, password, first_name, last_name, username, email, phone_number,
    date_joined, last_login, is_admin, is_staff, is_active, is_superadmin
) OVERRIDING SYSTEM VALUE VALUES
(101, 'pbkdf2_sha256$1500000$Ev5BmW6G2ViDc71WIszyaH$TUu/J6SGnPt184Se/F/FFVaxZKPYYs0xhTH/KUnjQ7w=',
 'Ananya', 'Sharma', 'ananya', 'ananya.sharma@example.com', '9876543210',
 TIMESTAMPTZ '2026-08-01 09:15:00+00', TIMESTAMPTZ '2026-08-01 09:15:00+00',
 false, false, true, false),
(102, 'pbkdf2_sha256$1500000$Ev5BmW6G2ViDc71WIszyaH$TUu/J6SGnPt184Se/F/FFVaxZKPYYs0xhTH/KUnjQ7w=',
 'Rahul', 'Mehta', 'rahul', 'rahul.mehta@example.com', '9811122233',
 TIMESTAMPTZ '2026-08-02 10:00:00+00', TIMESTAMPTZ '2026-08-02 10:00:00+00',
 false, false, true, false),
(103, 'pbkdf2_sha256$1500000$Ev5BmW6G2ViDc71WIszyaH$TUu/J6SGnPt184Se/F/FFVaxZKPYYs0xhTH/KUnjQ7w=',
 'Priya', 'Nair', 'priya', 'priya.nair@example.com', '9822233344',
 TIMESTAMPTZ '2026-08-03 11:30:00+00', TIMESTAMPTZ '2026-08-03 11:30:00+00',
 false, false, true, false),
(104, 'pbkdf2_sha256$1500000$Ev5BmW6G2ViDc71WIszyaH$TUu/J6SGnPt184Se/F/FFVaxZKPYYs0xhTH/KUnjQ7w=',
 'Arjun', 'Patel', 'arjun', 'arjun.patel@example.com', '9833344455',
 TIMESTAMPTZ '2026-08-04 08:45:00+00', TIMESTAMPTZ '2026-08-04 08:45:00+00',
 false, false, true, false),
(105, 'pbkdf2_sha256$1500000$Ev5BmW6G2ViDc71WIszyaH$TUu/J6SGnPt184Se/F/FFVaxZKPYYs0xhTH/KUnjQ7w=',
 'Meera', 'Khan', 'meera', 'meera.khan@example.com', '9844455566',
 TIMESTAMPTZ '2026-08-05 14:20:00+00', TIMESTAMPTZ '2026-08-05 14:20:00+00',
 false, false, true, false)
ON CONFLICT (id) DO NOTHING;

INSERT INTO accounts_userprofile (
    id, address_line_1, address_line_2, profile_picture, city, state, country, pin_code, user_id
) OVERRIDING SYSTEM VALUE VALUES
(101, '12 MG Road', 'Near City Center', 'default/default-user.png', 'Bengaluru', 'Karnataka', 'India', '560001', 101),
(102, '45 Linking Road', '', 'default/default-user.png', 'Mumbai', 'Maharashtra', 'India', '400050', 102),
(103, '88 Marine Drive', 'Apt 3B', 'default/default-user.png', 'Kochi', 'Kerala', 'India', '682001', 103),
(104, '7 CG Road', '', 'default/default-user.png', 'Ahmedabad', 'Gujarat', 'India', '380009', 104),
(105, '21 Park Street', 'Floor 2', 'default/default-user.png', 'Kolkata', 'West Bengal', 'India', '700016', 105)
ON CONFLICT (id) DO NOTHING;

INSERT INTO category_category (id, category_name, slug, description, cat_image) OVERRIDING SYSTEM VALUE VALUES
(101, 'T-Shirts', 'tshirts', 'Casual tees, shirts and hoodies.', ''),
(102, 'Jeans', 'jeans', 'Denim for everyday wear.', ''),
(103, 'Shoes', 'shoes', 'Sneakers and running shoes.', ''),
(104, 'Accessories', 'accessories', 'Watches, caps and extras.', '')
ON CONFLICT (id) DO NOTHING;

-- stock on product = sum of SKU stocks below
INSERT INTO store_product (
    id, product_name, slug, description, price, images, stock, is_available,
    created_date, modified_date, category_id
) OVERRIDING SYSTEM VALUE VALUES
(101, 'Classic Cotton Crew Tee', 'classic-cotton-crew-tee',
 'Breathable mid-weight cotton tee for daily wear. Color and size stocked separately.',
 499, '', 48, true, TIMESTAMPTZ '2026-08-10 06:00:00+00', TIMESTAMPTZ '2026-08-10 06:00:00+00', 101),
(102, 'Slim Fit Stretch Jeans', 'slim-fit-stretch-jeans',
 'Dark wash stretch denim. Sold by waist size only.',
 1499, '', 40, true, TIMESTAMPTZ '2026-08-10 06:05:00+00', TIMESTAMPTZ '2026-08-10 06:05:00+00', 102),
(103, 'Roadster Running Shoes', 'roadster-running-shoes',
 'Cushioned trainers for road runs. Stocked by color and UK size.',
 2499, '', 36, true, TIMESTAMPTZ '2026-08-10 06:10:00+00', TIMESTAMPTZ '2026-08-10 06:10:00+00', 103),
(104, 'Classic Analog Watch', 'classic-analog-watch',
 'Stainless steel analog watch. No size or color options.',
 1999, '', 25, true, TIMESTAMPTZ '2026-08-10 06:15:00+00', TIMESTAMPTZ '2026-08-10 06:15:00+00', 104),
(105, 'Fleece Pullover Hoodie', 'fleece-pullover-hoodie',
 'Soft fleece hoodie. Color only; one size fits most in this listing.',
 1299, '', 30, true, TIMESTAMPTZ '2026-08-10 06:20:00+00', TIMESTAMPTZ '2026-08-10 06:20:00+00', 101),
(106, 'Everyday Canvas Sneakers', 'everyday-canvas-sneakers',
 'Low-top canvas sneakers with gum sole.',
 899, '', 40, true, TIMESTAMPTZ '2026-08-10 06:25:00+00', TIMESTAMPTZ '2026-08-10 06:25:00+00', 103),
(107, 'Oxford Formal Shirt', 'oxford-formal-shirt',
 'Office oxford shirt. Collar sizes with two colors.',
 1099, '', 36, true, TIMESTAMPTZ '2026-08-10 06:30:00+00', TIMESTAMPTZ '2026-08-10 06:30:00+00', 101),
(108, 'Cotton Baseball Cap', 'cotton-baseball-cap',
 'Adjustable cotton cap. Color only.',
 399, '', 45, true, TIMESTAMPTZ '2026-08-10 06:35:00+00', TIMESTAMPTZ '2026-08-10 06:35:00+00', 104)
ON CONFLICT (id) DO NOTHING;

INSERT INTO store_variation (id, variation_category, variation_value, is_active, created_date, product_id)
OVERRIDING SYSTEM VALUE VALUES
-- 101 tee: color + size
(1001, 'color', 'Navy',  true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 101),
(1002, 'color', 'White', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 101),
(1003, 'color', 'Black', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 101),
(1004, 'size',  'S',     true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 101),
(1005, 'size',  'M',     true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 101),
(1006, 'size',  'L',     true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 101),
(1007, 'size',  'XL',    true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 101),
-- 102 jeans: size only
(1008, 'size', '30', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 102),
(1009, 'size', '32', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 102),
(1010, 'size', '34', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 102),
(1011, 'size', '36', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 102),
-- 103 shoes: color + size
(1012, 'color', 'Black', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 103),
(1013, 'color', 'Grey',  true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 103),
(1014, 'size',  '8',     true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 103),
(1015, 'size',  '9',     true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 103),
(1016, 'size',  '10',    true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 103),
-- 105 hoodie: color only
(1017, 'color', 'Grey',   true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 105),
(1018, 'color', 'Maroon', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 105),
(1019, 'color', 'Olive',  true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 105),
-- 106 sneakers: color + size
(1020, 'color', 'White', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 106),
(1021, 'color', 'Navy',  true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 106),
(1022, 'size',  '7',     true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 106),
(1023, 'size',  '8',     true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 106),
(1024, 'size',  '9',     true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 106),
(1025, 'size',  '10',    true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 106),
-- 107 formal shirt: color + collar size
(1026, 'color', 'Sky Blue', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 107),
(1027, 'color', 'White',    true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 107),
(1028, 'size',  '38',       true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 107),
(1029, 'size',  '40',       true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 107),
(1030, 'size',  '42',       true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 107),
-- 108 cap: color only
(1031, 'color', 'Black', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 108),
(1032, 'color', 'Beige', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 108),
(1033, 'color', 'Olive', true, TIMESTAMPTZ '2026-08-10 07:00:00+00', 108)
ON CONFLICT (id) DO NOTHING;

-- SKUs: raw SQL does not run Django signals, so stock rows must be inserted here.
INSERT INTO store_productsku (id, stock, is_active, product_id, color_id, size_id)
OVERRIDING SYSTEM VALUE VALUES
-- 101 tee 3x4 = 12 (total 48)
(2001, 4, true, 101, 1001, 1004),
(2002, 5, true, 101, 1001, 1005),
(2003, 4, true, 101, 1001, 1006),
(2004, 3, true, 101, 1001, 1007),
(2005, 4, true, 101, 1002, 1004),
(2006, 5, true, 101, 1002, 1005),
(2007, 4, true, 101, 1002, 1006),
(2008, 3, true, 101, 1002, 1007),
(2009, 4, true, 101, 1003, 1004),
(2010, 5, true, 101, 1003, 1005),
(2011, 4, true, 101, 1003, 1006),
(2012, 3, true, 101, 1003, 1007),
-- 102 jeans size only (total 40)
(2013, 8, true, 102, NULL, 1008),
(2014, 12, true, 102, NULL, 1009),
(2015, 12, true, 102, NULL, 1010),
(2016, 8, true, 102, NULL, 1011),
-- 103 shoes 2x3 = 6 (total 36)
(2017, 6, true, 103, 1012, 1014),
(2018, 7, true, 103, 1012, 1015),
(2019, 5, true, 103, 1012, 1016),
(2020, 6, true, 103, 1013, 1014),
(2021, 7, true, 103, 1013, 1015),
(2022, 5, true, 103, 1013, 1016),
-- 104 watch: default SKU (total 25)
(2023, 25, true, 104, NULL, NULL),
-- 105 hoodie color only (total 30)
(2024, 10, true, 105, 1017, NULL),
(2025, 10, true, 105, 1018, NULL),
(2026, 10, true, 105, 1019, NULL),
-- 106 sneakers 2x4 = 8 (total 40)
(2027, 5, true, 106, 1020, 1022),
(2028, 5, true, 106, 1020, 1023),
(2029, 5, true, 106, 1020, 1024),
(2030, 5, true, 106, 1020, 1025),
(2031, 5, true, 106, 1021, 1022),
(2032, 5, true, 106, 1021, 1023),
(2033, 5, true, 106, 1021, 1024),
(2034, 5, true, 106, 1021, 1025),
-- 107 shirt 2x3 = 6 (total 36)
(2035, 6, true, 107, 1026, 1028),
(2036, 6, true, 107, 1026, 1029),
(2037, 6, true, 107, 1026, 1030),
(2038, 6, true, 107, 1027, 1028),
(2039, 6, true, 107, 1027, 1029),
(2040, 6, true, 107, 1027, 1030),
-- 108 cap color only (total 45)
(2041, 15, true, 108, 1031, NULL),
(2042, 15, true, 108, 1032, NULL),
(2043, 15, true, 108, 1033, NULL)
ON CONFLICT (id) DO NOTHING;

SELECT setval('accounts_account_id_seq',     (SELECT MAX(id) FROM accounts_account));
SELECT setval('accounts_userprofile_id_seq', (SELECT MAX(id) FROM accounts_userprofile));
SELECT setval('category_category_id_seq',    (SELECT MAX(id) FROM category_category));
SELECT setval('store_product_id_seq',        (SELECT MAX(id) FROM store_product));
SELECT setval('store_variation_id_seq',      (SELECT MAX(id) FROM store_variation));
SELECT setval('store_productsku_id_seq',     (SELECT MAX(id) FROM store_productsku));

COMMIT;
