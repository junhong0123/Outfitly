using Microsoft.AspNetCore.Mvc;
using Outfitly.Models;

namespace Outfitly.Controllers
{
    public class AccountController : Controller
    {
        // GET: Account/Orders
        public IActionResult Orders(string? status = null, int page = 1)
        {
            // TODO: Get actual user orders from database
            var orders = GetSampleOrders();

            // Filter by status if provided
            if (!string.IsNullOrEmpty(status) && status != "all")
            {
                orders = orders.Where(o => o.Status.ToLower() == status.ToLower()).ToList();
            }

            // TODO: Implement pagination
            // var pagedOrders = orders.Skip((page - 1) * pageSize).Take(pageSize).ToList();

            return View(orders);
        }

        // GET: Account/OrderDetails/{id}
        public IActionResult OrderDetails(int id)
        {
            // TODO: Get actual order from database
            var order = GetSampleOrders().FirstOrDefault(o => o.Id == id);

            if (order == null)
            {
                return NotFound();
            }

            return View(order);
        }

        // GET: Account/Profile
        public IActionResult Profile()
        {
            // TODO: Get actual user profile from database
            return View();
        }

        // POST: Account/CancelOrder
        [HttpPost]
        public IActionResult CancelOrder(int orderId)
        {
            // TODO: Implement order cancellation logic
            // 1. Check if order can be cancelled (only if status is "Pending" or "Processing")
            // 2. Update order status to "Cancelled"
            // 3. Process refund
            // 4. Send cancellation email

            return Json(new
            {
                success = true,
                message = "Order cancelled successfully. Refund will be processed within 3-5 business days."
            });
        }

        // POST: Account/TrackOrder
        [HttpPost]
        public IActionResult TrackOrder(int orderId)
        {
            // TODO: Get actual tracking information from shipping provider
            var trackingInfo = new
            {
                trackingNumber = "TRK123456789",
                carrier = "Express Shipping",
                status = "Out for Delivery",
                estimatedDelivery = DateTime.Now.AddDays(2).ToString("MMM dd, yyyy"),
                updates = new[]
                {
                    new { date = "Nov 08, 2025 - 10:30 AM", location = "Local Facility", status = "Out for Delivery" },
                    new { date = "Nov 07, 2025 - 3:45 PM", location = "Distribution Center", status = "In Transit" },
                    new { date = "Nov 06, 2025 - 9:20 AM", location = "Origin Facility", status = "Picked Up" }
                }
            };

            return Json(new { success = true, tracking = trackingInfo });
        }

        // GET: Account/Dashboard
        public IActionResult Dashboard()
        {
            // TODO: Get actual user dashboard data from database
            var dashboardData = new DashboardViewModel
            {
                UserName = "John Doe",
                UserEmail = "john@example.com",
                TotalOrders = 12,
                PendingOrders = 2,
                TotalSpent = 2459.00m,
                RecentOrders = GetSampleOrders().Take(3).ToList(),
                DefaultAddress = new ShippingAddress
                {
                    FirstName = "John",
                    LastName = "Doe",
                    AddressLine1 = "123 Main Street",
                    AddressLine2 = "Apartment 4B",
                    City = "New York",
                    StateProvince = "NY",
                    ZipPostalCode = "10001",
                    Country = "United States",
                    PhoneNumber = "+1 (555) 123-4567",
                    Email = "john@example.com"
                }
            };

            return View(dashboardData);
        }

        // Sample orders for testing
        private List<Order> GetSampleOrders()
        {
            return new List<Order>
            {
                new Order
                {
                    Id = 1,
                    OrderNumber = "#12345",
                    OrderDate = new DateTime(2025, 11, 1),
                    CustomerName = "John Doe",
                    CustomerEmail = "john@example.com",
                    Status = "Processing",
                    Subtotal = 356.00m,
                    ShippingCost = 10.00m,
                    Tax = 35.60m,
                    Total = 401.60m,
                    ShippingAddressLine1 = "123 Main Street",
                    ShippingCity = "New York",
                    ShippingState = "NY",
                    ShippingZipCode = "10001",
                    ShippingCountry = "United States",
                    OrderItems = new List<OrderItem>
                    {
                        new OrderItem
                        {
                            ProductId = 1,
                            ProductName = "Minimal Cotton Tee",
                            Price = 49.00m,
                            Quantity = 1,
                            Color = "Black",
                            Size = "M"
                        },
                        new OrderItem
                        {
                            ProductId = 2,
                            ProductName = "Tailored Linen Pants",
                            Price = 89.00m,
                            Quantity = 2,
                            Color = "Blue",
                            Size = "L"
                        }
                    }
                },
                new Order
                {
                    Id = 2,
                    OrderNumber = "#12344",
                    OrderDate = new DateTime(2025, 10, 28),
                    CustomerName = "John Doe",
                    CustomerEmail = "john@example.com",
                    Status = "Shipped",
                    Subtotal = 129.00m,
                    ShippingCost = 0m,
                    Tax = 12.90m,
                    Total = 141.90m,
                    ShippedDate = new DateTime(2025, 11, 5),
                    TrackingNumber = "TRK123456789",
                    ShippingAddressLine1 = "123 Main Street",
                    ShippingCity = "New York",
                    ShippingState = "NY",
                    ShippingZipCode = "10001",
                    ShippingCountry = "United States",
                    OrderItems = new List<OrderItem>
                    {
                        new OrderItem
                        {
                            ProductId = 3,
                            ProductName = "Leather Crossbody Bag",
                            Price = 129.00m,
                            Quantity = 1,
                            Color = "Brown",
                            Size = "One Size"
                        }
                    }
                },
                new Order
                {
                    Id = 3,
                    OrderNumber = "#12343",
                    OrderDate = new DateTime(2025, 10, 20),
                    CustomerName = "John Doe",
                    CustomerEmail = "john@example.com",
                    Status = "Delivered",
                    Subtotal = 249.00m,
                    ShippingCost = 0m,
                    Tax = 24.90m,
                    Total = 273.90m,
                    ShippedDate = new DateTime(2025, 10, 22),
                    DeliveredDate = new DateTime(2025, 10, 25),
                    TrackingNumber = "TRK987654321",
                    ShippingAddressLine1 = "123 Main Street",
                    ShippingCity = "New York",
                    ShippingState = "NY",
                    ShippingZipCode = "10001",
                    ShippingCountry = "United States",
                    OrderItems = new List<OrderItem>
                    {
                        new OrderItem
                        {
                            ProductId = 4,
                            ProductName = "Classic Wool Coat",
                            Price = 249.00m,
                            Quantity = 1,
                            Color = "Gray",
                            Size = "M"
                        }
                    }
                },
                new Order
                {
                    Id = 4,
                    OrderNumber = "#12342",
                    OrderDate = new DateTime(2025, 10, 15),
                    CustomerName = "John Doe",
                    CustomerEmail = "john@example.com",
                    Status = "Cancelled",
                    Subtotal = 79.00m,
                    ShippingCost = 10.00m,
                    Tax = 7.90m,
                    Total = 96.90m,
                    ShippingAddressLine1 = "123 Main Street",
                    ShippingCity = "New York",
                    ShippingState = "NY",
                    ShippingZipCode = "10001",
                    ShippingCountry = "United States",
                    OrderItems = new List<OrderItem>
                    {
                        new OrderItem
                        {
                            ProductId = 5,
                            ProductName = "Silk Blend Blouse",
                            Price = 79.00m,
                            Quantity = 1,
                            Color = "White",
                            Size = "S"
                        }
                    }
                }
            };
        }
    }
}