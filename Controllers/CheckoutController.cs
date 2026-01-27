using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;
using System.Security.Claims;
using Outfitly.Data;
using Outfitly.Models;

namespace Outfitly.Controllers
{
    [Authorize]
    public class CheckoutController : Controller
    {
        private readonly ApplicationDbContext _context;

        public CheckoutController(ApplicationDbContext context)
        {
            _context = context;
        }

        // GET: Checkout
        public async Task<IActionResult> Index()
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userId))
            {
                return RedirectToAction("Login", "Account");
            }

            // Get cart items for this user
            var cartItems = await _context.CartItems
                .Where(c => c.Id.ToString().StartsWith(userId.Substring(0, 8))) // Simple cart association
                .ToListAsync();

            // If cart is empty, redirect to cart page
            if (!cartItems.Any())
            {
                TempData["Error"] = "Your cart is empty. Add items before checking out.";
                return RedirectToAction("Index", "Cart");
            }

            // Get user's saved addresses (max 3)
            var savedAddresses = await _context.SavedAddresses
                .Where(a => a.UserId == userId)
                .OrderByDescending(a => a.CreatedAt)
                .Take(3)
                .ToListAsync();

            var cart = new Cart { Items = cartItems };

            var viewModel = new CheckoutViewModel
            {
                Cart = cart,
                SavedAddresses = savedAddresses
            };

            return View(viewModel);
        }

        // POST: Checkout/ProcessOrder
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> ProcessOrder(CheckoutViewModel model)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userId))
            {
                return RedirectToAction("Login", "Account");
            }

            // Re-populate saved addresses for validation errors
            model.SavedAddresses = await _context.SavedAddresses
                .Where(a => a.UserId == userId)
                .OrderByDescending(a => a.CreatedAt)
                .Take(3)
                .ToListAsync();

            if (!ModelState.IsValid)
            {
                // Re-populate cart
                var cartItems = await _context.CartItems.ToListAsync();
                model.Cart = new Cart { Items = cartItems };
                return View("Index", model);
            }

            // Get cart items
            var userCartItems = await _context.CartItems.ToListAsync();
            if (!userCartItems.Any())
            {
                TempData["Error"] = "Your cart is empty.";
                return RedirectToAction("Index", "Cart");
            }

            // Begin transaction
            using var transaction = await _context.Database.BeginTransactionAsync();

            try
            {
                // 1. Address Logic: Save address if requested (max 3)
                if (model.SaveAddress)
                {
                    var existingAddressCount = await _context.SavedAddresses
                        .CountAsync(a => a.UserId == userId);

                    // Only save if user has less than 3 addresses (Ignore if 3 exist)
                    if (existingAddressCount < 3)
                    {
                        var newAddress = new SavedAddress
                        {
                            UserId = userId,
                            FirstName = model.ShippingAddress.FirstName,
                            LastName = model.ShippingAddress.LastName,
                            AddressLine1 = model.ShippingAddress.AddressLine1,
                            AddressLine2 = model.ShippingAddress.AddressLine2,
                            City = model.ShippingAddress.City,
                            State = model.ShippingAddress.StateProvince,
                            Zip = model.ShippingAddress.ZipPostalCode,
                            Country = model.ShippingAddress.Country,
                            CreatedAt = DateTime.UtcNow
                        };
                        _context.SavedAddresses.Add(newAddress);
                    }
                }

                // 2. Create Order record
                var order = new Order
                {
                    OrderNumber = GenerateOrderNumber(),
                    OrderDate = DateTime.UtcNow,
                    CustomerId = userId,
                    CustomerName = $"{model.ShippingAddress.FirstName} {model.ShippingAddress.LastName}",
                    CustomerEmail = model.ShippingAddress.Email,
                    ShippingAddressLine1 = model.ShippingAddress.AddressLine1,
                    ShippingAddressLine2 = model.ShippingAddress.AddressLine2,
                    ShippingCity = model.ShippingAddress.City,
                    ShippingState = model.ShippingAddress.StateProvince,
                    ShippingZipCode = model.ShippingAddress.ZipPostalCode,
                    ShippingCountry = model.ShippingAddress.Country,
                    PaymentMethod = model.PaymentInfo.PaymentMethod,
                    TransactionId = Guid.NewGuid().ToString(),
                    Subtotal = userCartItems.Sum(i => i.TotalPrice),
                    ShippingCost = userCartItems.Sum(i => i.TotalPrice) >= 100 ? 0 : 10.00m,
                    Tax = userCartItems.Sum(i => i.TotalPrice) * 0.10m,
                    Discount = model.PromoDiscount,
                    Status = "Pending"
                };

                order.Total = order.Subtotal + order.ShippingCost + order.Tax - order.Discount;
                _context.Orders.Add(order);
                await _context.SaveChangesAsync();

                // 3. Move CartItems to OrderItems and deduct stock
                foreach (var cartItem in userCartItems)
                {
                    // Create OrderItem
                    var orderItem = new OrderItem
                    {
                        OrderId = order.Id,
                        ProductId = cartItem.ProductId,
                        ProductName = cartItem.ProductName,
                        Price = cartItem.Price,
                        Quantity = cartItem.Quantity,
                        Color = cartItem.Color,
                        Size = cartItem.Size,
                        ImageUrl = cartItem.ImageUrl
                    };
                    _context.OrderItems.Add(orderItem);

                    // Deduct stock from Product
                    var product = await _context.Products.FindAsync(cartItem.ProductId);
                    if (product != null)
                    {
                        product.StockQuantity = Math.Max(0, product.StockQuantity - cartItem.Quantity);
                    }
                }

                // 4. Clear cart
                _context.CartItems.RemoveRange(userCartItems);

                await _context.SaveChangesAsync();
                await transaction.CommitAsync();

                TempData["OrderId"] = order.Id;
                TempData["SuccessMessage"] = "Your order has been placed successfully!";

                return RedirectToAction("Confirmation", new { id = order.Id });
            }
            catch (Exception)
            {
                await transaction.RollbackAsync();
                ModelState.AddModelError("", "An error occurred while processing your order. Please try again.");

                // Re-populate cart
                model.Cart = new Cart { Items = userCartItems };
                return View("Index", model);
            }
        }

        // GET: Checkout/Confirmation/{id}
        public async Task<IActionResult> Confirmation(int id)
        {
            var order = await _context.Orders
                .Include(o => o.OrderItems)
                .FirstOrDefaultAsync(o => o.Id == id);

            if (order == null)
            {
                return NotFound();
            }

            var confirmation = new OrderConfirmation
            {
                OrderId = order.Id,
                OrderDate = order.OrderDate,
                TotalAmount = order.Total,
                Status = order.Status,
                EstimatedDelivery = order.OrderDate.AddDays(5),
                ShippingAddress = new ShippingAddress
                {
                    FirstName = order.CustomerName.Split(' ').FirstOrDefault() ?? "",
                    LastName = order.CustomerName.Split(' ').LastOrDefault() ?? "",
                    AddressLine1 = order.ShippingAddressLine1,
                    City = order.ShippingCity,
                    StateProvince = order.ShippingState,
                    ZipPostalCode = order.ShippingZipCode,
                    Country = order.ShippingCountry
                },
                Items = order.OrderItems.Select(oi => new CartItem
                {
                    ProductId = oi.ProductId,
                    ProductName = oi.ProductName,
                    Price = oi.Price,
                    Quantity = oi.Quantity,
                    Color = oi.Color,
                    Size = oi.Size,
                    ImageUrl = oi.ImageUrl
                }).ToList()
            };

            return View(confirmation);
        }

        // GET: Checkout/GetSavedAddress/{id}
        [HttpGet]
        public async Task<IActionResult> GetSavedAddress(int id)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            var address = await _context.SavedAddresses
                .FirstOrDefaultAsync(a => a.Id == id && a.UserId == userId);

            if (address == null)
            {
                return NotFound();
            }

            return Json(new
            {
                firstName = address.FirstName,
                lastName = address.LastName,
                addressLine1 = address.AddressLine1,
                addressLine2 = address.AddressLine2 ?? "",
                city = address.City,
                state = address.State,
                zip = address.Zip,
                country = address.Country
            });
        }

        // POST: Checkout/ValidateAddress
        [HttpPost]
        public IActionResult ValidateAddress([FromBody] ShippingAddress address)
        {
            if (string.IsNullOrWhiteSpace(address.FirstName) ||
                string.IsNullOrWhiteSpace(address.LastName))
            {
                return Json(new { success = false, message = "Name is required" });
            }

            return Json(new { success = true, message = "Address is valid" });
        }

        // POST: Checkout/CalculateShipping
        [HttpPost]
        public IActionResult CalculateShipping([FromBody] ShippingAddress address)
        {
            decimal shippingCost = 10.00m; // Default shipping

            return Json(new
            {
                success = true,
                shippingCost = shippingCost,
                estimatedDays = 5
            });
        }

        // POST: Checkout/ProcessPayment
        [HttpPost]
        public IActionResult ProcessPayment([FromBody] PaymentInfo payment)
        {
            if (string.IsNullOrWhiteSpace(payment.CardNumber))
            {
                return Json(new { success = false, message = "Card number is required" });
            }

            // Simulate payment processing
            System.Threading.Thread.Sleep(1000);

            var transactionId = Guid.NewGuid().ToString();

            return Json(new
            {
                success = true,
                transactionId = transactionId,
                message = "Payment processed successfully"
            });
        }

        // POST: Checkout/ApplyPromoCode
        [HttpPost]
        public IActionResult ApplyPromoCode([FromBody] PromoCodeRequest request)
        {
            var validCodes = new Dictionary<string, decimal>
            {
                { "SAVE10", 10.00m },
                { "SAVE20", 20.00m },
                { "FREESHIP", 10.00m }
            };

            if (validCodes.ContainsKey(request.Code.ToUpper()))
            {
                var discount = validCodes[request.Code.ToUpper()];
                return Json(new
                {
                    success = true,
                    discount = discount,
                    message = $"Promo code applied! You saved ${discount:F2}"
                });
            }

            return Json(new
            {
                success = false,
                message = "Invalid promo code"
            });
        }

        private string GenerateOrderNumber()
        {
            var timestamp = DateTime.UtcNow.ToString("yyyyMMddHHmmss");
            var random = new Random().Next(1000, 9999);
            return $"ORD-{timestamp}-{random}";
        }
    }

    // Request models for API endpoints
    public class PromoCodeRequest
    {
        public string Code { get; set; } = string.Empty;
    }
}