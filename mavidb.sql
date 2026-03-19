CREATE TABLE Store (
    Store_ID INT PRIMARY KEY AUTO_INCREMENT,
    Store_Name VARCHAR(100) NOT NULL,
    Location VARCHAR(150) NOT NULL
);

CREATE TABLE Employee (
    Employee_ID INT PRIMARY KEY AUTO_INCREMENT,
    First_Name VARCHAR(50) NOT NULL,
    Last_Name VARCHAR(50) NOT NULL,
    Role VARCHAR(20) NOT NULL,
    Store_ID INT NOT NULL,
	Username VARCHAR(50) NOT NULL UNIQUE,
    Password VARCHAR(255),
    FOREIGN KEY (Store_ID) REFERENCES Store(Store_ID)
);

CREATE TABLE Supplier (
    Supplier_ID INT PRIMARY KEY AUTO_INCREMENT,
    Supplier_Name VARCHAR(100) NOT NULL,
    Contact_Person VARCHAR(100),
    Phone VARCHAR(20),
    Email VARCHAR(100)
);

CREATE TABLE Product (
    Product_ID INT PRIMARY KEY AUTO_INCREMENT,
    Product_Name VARCHAR(100) NOT NULL,
    Size VARCHAR(20),
    Default_Sale_Price DECIMAL(10,2) NOT NULL,
    Reorder_Level INT NOT NULL,
    Supplier_ID INT NOT NULL,
    Category VARCHAR(50),
    Unit_Cost DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (Supplier_ID) REFERENCES Supplier(Supplier_ID)
);

CREATE TABLE Warehouse (
    Warehouse_ID INT PRIMARY KEY AUTO_INCREMENT,
    Location VARCHAR(150) NOT NULL
);

CREATE TABLE Inventory (
    Inventory_ID INT PRIMARY KEY AUTO_INCREMENT,
    Product_ID INT NOT NULL,
    Warehouse_ID INT,
    Store_ID INT,
    Quantity_Available INT NOT NULL,
    FOREIGN KEY (Product_ID) REFERENCES Product(Product_ID),
    FOREIGN KEY (Warehouse_ID) REFERENCES Warehouse(Warehouse_ID),
    FOREIGN KEY (Store_ID) REFERENCES Store(Store_ID)
);

CREATE TABLE Purchase (
    Purchase_ID INT PRIMARY KEY AUTO_INCREMENT,
    Supplier_ID INT NOT NULL,
    Warehouse_ID INT NOT NULL,
    Purchase_Date DATE NOT NULL,
    Employee_ID INT NOT NULL,
    Purchase_Subtotal DECIMAL(10,2),
    UNIQUE(Purchase_ID, Product_ID),
    FOREIGN KEY (Supplier_ID) REFERENCES Supplier(Supplier_ID),
    FOREIGN KEY (Warehouse_ID) REFERENCES Warehouse(Warehouse_ID),
    FOREIGN KEY (Employee_ID) REFERENCES Employee(Employee_ID)
);

CREATE TABLE Purchase_Details (
    PurchaseDetails_ID INT PRIMARY KEY AUTO_INCREMENT,
    Purchase_ID INT NOT NULL,
    Product_ID INT NOT NULL,
    Quantity INT NOT NULL,
    Unit_Cost DECIMAL(10,2) NOT NULL,
	UNIQUE (PurchaseDetails_ID, Purchase_ID),
    FOREIGN KEY (Purchase_ID) REFERENCES Purchase(Purchase_ID),
    FOREIGN KEY (Product_ID) REFERENCES Product(Product_ID)
);

CREATE TABLE Customer (
    Customer_ID INT PRIMARY KEY AUTO_INCREMENT,
    First_Name VARCHAR(50) NOT NULL,
    Last_Name VARCHAR(50) NOT NULL,
    Phone VARCHAR(20)
);

CREATE TABLE Sale (
    Sale_ID INT PRIMARY KEY AUTO_INCREMENT,
    Customer_ID INT NOT NULL,
    Employee_ID INT NOT NULL,
    Store_ID INT NOT NULL,
    Sale_Date DATE NOT NULL,
    Sale_Payment_Method VARCHAR(30),
    FOREIGN KEY (Customer_ID) REFERENCES Customer(Customer_ID),
    FOREIGN KEY (Employee_ID) REFERENCES Employee(Employee_ID),
    FOREIGN KEY (Store_ID) REFERENCES Store(Store_ID)
);

CREATE TABLE Sale_Details (
    SaleDetails_ID INT PRIMARY KEY AUTO_INCREMENT,
    Sale_ID INT NOT NULL,
    Product_ID INT NOT NULL,
    Quantity INT NOT NULL,
    Unit_Price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (Sale_ID) REFERENCES Sale(Sale_ID),
    FOREIGN KEY (Product_ID) REFERENCES Product(Product_ID)
);

CREATE TABLE Stock_Transfer (
    Transfer_ID INT PRIMARY KEY AUTO_INCREMENT,
    Warehouse_ID INT NOT NULL,
    Store_ID INT NOT NULL,
    Transfer_Date DATE NOT NULL,
    Employee_ID INT NOT NULL,
    FOREIGN KEY (Warehouse_ID) REFERENCES Warehouse(Warehouse_ID),
    FOREIGN KEY (Store_ID) REFERENCES Store(Store_ID),
    FOREIGN KEY (Employee_ID) REFERENCES Employee(Employee_ID)
);

CREATE TABLE Stock_Transfer_Details (
    TransferDetails_ID INT PRIMARY KEY AUTO_INCREMENT,
    Transfer_ID INT NOT NULL,
    Product_ID INT NOT NULL,
    Quantity_Transferred INT NOT NULL,
    UNIQUE (TransferDetails_ID, Product_ID),
    FOREIGN KEY (Transfer_ID) REFERENCES Stock_Transfer(Transfer_ID),
    FOREIGN KEY (Product_ID) REFERENCES Product(Product_ID)
);

CREATE TABLE Payment (
    Payment_ID INT PRIMARY KEY AUTO_INCREMENT,
    Purchase_ID INT NOT NULL,
    Payment_Method VARCHAR(30) NOT NULL,
    Payment_Amount DECIMAL(10,2) NOT NULL,
    Payment_Date DATE NOT NULL,
    FOREIGN KEY (Purchase_ID) REFERENCES Purchase(Purchase_ID) ON DELETE CASCADE
);

INSERT INTO Store (Store_Name, Location)
VALUES ('Mavi Store - Ramallah', 'Al quliyeh al ahliyeh street City');

INSERT INTO Warehouse (Location)
VALUES ('Ramallah Central Warehouse');

INSERT INTO Supplier (Supplier_Name, Contact_Person, Phone, Email)
VALUES ('Mavi Denim Manufacturing Turkey', 'Emre Yıldız', '+90 212 555 7834', 'supply.turkey@mavidenim.com');

INSERT INTO Employee
(First_Name, Last_Name, Store_ID, Role, Username, Password)
VALUES
('Omar', 'Khalil', 1, 'admin', 'omar.khalil', '1234'),
('Sara', 'Nasser', 1, 'user', 'sara.nasser', '1234'),
('Ahmad', 'Saleh', 1, 'user', 'ahmad.saleh', '1234');

INSERT INTO Product
(Product_ID, Product_Name, Size, Reorder_Level, Supplier_ID, Category, Unit_Cost, Default_Sale_Price)
VALUES
(1, 'Men Hoodie', 'L', 20, 1, 'Hoodies', 120.00, 180.00),
(2, 'Women Jacket', 'M', 15, 1, 'Jackets', 170.00, 250.00),
(3, 'Men Jeans', '32', 25, 1, 'Jeans', 140.00, 200.00),
(4, 'Men Hoodie', 'S', 20, 1, 'Hoodies', 115.00, 180.00),
(5, 'Men Hoodie', 'M', 20, 1, 'Hoodies', 125.00, 180.00),
(6, 'Women Jacket', 'XL', 15, 1, 'Jackets', 160.00, 250.00);

INSERT INTO Inventory (Product_ID, Warehouse_ID, Store_ID, Quantity_Available) VALUES
(1, 1, NULL, 100),
(2, 1, NULL, 80),
(3, 1, NULL, 120),
(1, NULL, 1, 30),
(2, NULL, 1, 25),
(3, NULL, 1, 40);

INSERT INTO Purchase
(Purchase_ID, Supplier_ID, Warehouse_ID, Purchase_Date, Employee_ID)
VALUES
(1, 1, 1, '2025-01-05', 1),
(2, 1, 1, '2025-02-05', 2),
(3, 1, 1, '2025-08-05', 1),
(6, 1, 1, '2025-09-20', 1);

INSERT INTO Purchase_Details
(PurchaseDetails_ID, Purchase_ID, Product_ID, Quantity, Unit_Cost)
VALUES
(1, 1, 1, 50, 150.00),
(2, 1, 3, 40, 160.00),
(3, 2, 1, 4, 150.00),
(5, 3, 5, 50, 50.00),
(6, 3, 6, 50, 70.00),
(10, 2, 4, 20, 50.00),
(12, 3, 4, 10, 70.00),
(13, 2, 5, 50, 125.00),
(16, 2, 6, 5, 160.00),
(19, 6, 3, 100, 140.00),
(20, 6, 5, 50, 125.00);

INSERT INTO Payment
(Payment_ID, Purchase_ID, Payment_Method, Payment_Amount, Payment_Date)
VALUES
(1, 1, 'Bank Transfer', 12000.00, '2025-01-06'),
(6, 3, 'Bank Transfer', 2300.00, '2026-05-02'),
(7, 2, 'Cheque', 2500.00, '2025-05-05'),
(9, 6, 'Cheque', 11000.00, '2025-02-05');

INSERT INTO Customer (First_Name, Last_Name, Phone) VALUES
('Mohammad', 'Salameh', '0599887766'),
('Rania', 'Abu Eid', '0599443322');

INSERT INTO Sale
(Sale_ID, Customer_ID, Employee_ID, Store_ID, Sale_Date, Sale_Payment_Method)
VALUES
(1, 1, 1, 1, '2025-01-10', 'Cash'),
(2, 3, 1, 1, '2026-01-16', 'Cash'),
(5, 4, 1, 1, '2026-01-18', 'Cash'),
(6, 5, 1, 1, '2025-08-29', 'Cash');

INSERT INTO Sale_Details
(SaleDetails_ID, Sale_ID, Product_ID, Quantity, Unit_Price)
VALUES
(1, 1, 1, 1, 200.00),
(2, 1, 3, 1, 200.00),
(3, 2, 1, 1, 180.00),
(4, 2, 3, 1, 200.00),
(9, 5, 6, 1, 250.00),
(10, 6, 1, 1, 180.00);

INSERT INTO Stock_Transfer
(Warehouse_ID, Store_ID, Transfer_Date, Employee_ID)
VALUES
(1, 1, '2025-01-07', 1);

INSERT INTO Stock_Transfer_Details
(TransferDetails_ID, Transfer_ID, Product_ID, Quantity_Transferred)
VALUES
(1, 1, 1, 20),
(2, 1, 2, 15),
(6, 2, 5, 50),
(7, 3, 6, 110),
(10, 4, 2, 20),
(16, 4, 1, 30);
