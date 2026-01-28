using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using Outfitly.Models;

namespace Outfitly.Data
{
    public class ApplicationDbContext : IdentityDbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        public DbSet<CartItem> CartItems { get; set; } = default!;
        public DbSet<Product> Products { get; set; } = default!;
        public DbSet<Order> Orders { get; set; } = default!;
        public DbSet<OrderItem> OrderItems { get; set; } = default!;
        public DbSet<SavedAddress> SavedAddresses { get; set; } = default!;

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            // Configure Order -> OrderItems relationship
            modelBuilder.Entity<Order>()
                .HasMany(o => o.OrderItems)
                .WithOne()
                .HasForeignKey(oi => oi.OrderId)
                .OnDelete(DeleteBehavior.Cascade);

            // Configure Product -> Colors/Sizes as JSON (for EF Core 9)
            modelBuilder.Entity<Product>()
                .Property(p => p.AvailableColors)
                .HasConversion(
                    v => string.Join(',', v),
                    v => v.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList());

            modelBuilder.Entity<Product>()
                .Property(p => p.AvailableSizes)
                .HasConversion(
                    v => string.Join(',', v),
                    v => v.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList());

            // Seed Products
            modelBuilder.Entity<Product>().HasData(
                new Product
                {
                    Id = 1,
                    Name = "Classic White Tee",
                    Description = "A premium quality cotton t-shirt for everyday wear.",
                    Price = 29.99m,
                    Category = "Tops",
                    AvailableColors = new List<string> { "White", "Black", "Gray" },
                    AvailableSizes = new List<string> { "S", "M", "L", "XL" },
                    StockQuantity = 100,
                    ImageUrl = "https://placehold.co/600x400?text=White+Tee",
                    CreatedAt = new DateTime(2024, 1, 1)
                },
                new Product
                {
                    Id = 2,
                    Name = "Slim Fit Jeans",
                    Description = "Comfortable slim fit jeans with a modern look.",
                    Price = 59.99m,
                    Category = "Bottoms",
                    AvailableColors = new List<string> { "Blue", "Black" },
                    AvailableSizes = new List<string> { "30", "32", "34", "36" },
                    StockQuantity = 50,
                    ImageUrl = "https://placehold.co/600x400?text=Jeans",
                    CreatedAt = new DateTime(2024, 1, 1)
                },
                new Product
                {
                    Id = 3,
                    Name = "Lightweight Bomber Jacket",
                    Description = "Perfect for chilly evenings, this jacket is both stylish and functional.",
                    Price = 89.99m,
                    Category = "Outerwear",
                    AvailableColors = new List<string> { "Navy", "Olive" },
                    AvailableSizes = new List<string> { "M", "L", "XL" },
                    StockQuantity = 30,
                    ImageUrl = "https://placehold.co/600x400?text=Jacket",
                    CreatedAt = new DateTime(2024, 1, 1)
                },
                new Product
                {
                    Id = 4,
                    Name = "Running Sneakers",
                    Description = "High-performance running shoes with excellent cushioning.",
                    Price = 79.99m,
                    Category = "Footwear",
                    AvailableColors = new List<string> { "Red", "Blue", "White" },
                    AvailableSizes = new List<string> { "8", "9", "10", "11" },
                    StockQuantity = 40,
                    ImageUrl = "https://placehold.co/600x400?text=Sneakers",
                    CreatedAt = new DateTime(2024, 1, 1)
                },
                new Product
                {
                    Id = 5,
                    Name = "Summer Floral Dress",
                    Description = "A breezy and beautiful dress for summer outings.",
                    Price = 49.99m,
                    Category = "Dresses",
                    AvailableColors = new List<string> { "Pink", "Yellow" },
                    AvailableSizes = new List<string> { "XS", "S", "M" },
                    StockQuantity = 25,
                    ImageUrl = "https://placehold.co/600x400?text=Summer+Dress",
                    CreatedAt = new DateTime(2024, 1, 1)
                },
                new Product
                {
                    Id = 6,
                    Name = "Tailored Linen Pants",
                    Description = "Elegant linen pants perfect for business casual.",
                    Price = 89.00m,
                    Category = "Bottoms",
                    AvailableColors = new List<string> { "Blue", "Gray", "Beige" },
                    AvailableSizes = new List<string> { "S", "M", "L", "XL" },
                    StockQuantity = 45,
                    ImageUrl = "https://placehold.co/600x400?text=Linen+Pants",
                    CreatedAt = new DateTime(2024, 1, 2)
                },
                new Product
                {
                    Id = 7,
                    Name = "Leather Crossbody Bag",
                    Description = "Genuine leather crossbody bag with adjustable strap.",
                    Price = 129.00m,
                    Category = "Accessories",
                    AvailableColors = new List<string> { "Brown", "Black", "Tan" },
                    AvailableSizes = new List<string> { "One Size" },
                    StockQuantity = 20,
                    ImageUrl = "https://placehold.co/600x400?text=Crossbody+Bag",
                    CreatedAt = new DateTime(2024, 1, 2)
                },
                new Product
                {
                    Id = 8,
                    Name = "Classic Wool Coat",
                    Description = "Timeless wool coat for the winter season.",
                    Price = 249.00m,
                    Category = "Outerwear",
                    AvailableColors = new List<string> { "Gray", "Navy", "Camel" },
                    AvailableSizes = new List<string> { "S", "M", "L" },
                    StockQuantity = 15,
                    ImageUrl = "https://placehold.co/600x400?text=Wool+Coat",
                    CreatedAt = new DateTime(2024, 1, 3)
                },
                new Product
                {
                    Id = 9,
                    Name = "Silk Blend Blouse",
                    Description = "Luxurious silk blend blouse for formal occasions.",
                    Price = 79.00m,
                    Category = "Tops",
                    AvailableColors = new List<string> { "White", "Pink", "Cream" },
                    AvailableSizes = new List<string> { "XS", "S", "M", "L" },
                    StockQuantity = 35,
                    ImageUrl = "https://placehold.co/600x400?text=Silk+Blouse",
                    CreatedAt = new DateTime(2024, 1, 3)
                },
                new Product
                {
                    Id = 10,
                    Name = "Denim Jacket",
                    Description = "Classic denim jacket that never goes out of style.",
                    Price = 119.00m,
                    Category = "Outerwear",
                    AvailableColors = new List<string> { "Blue", "Black" },
                    AvailableSizes = new List<string> { "S", "M", "L", "XL" },
                    StockQuantity = 40,
                    ImageUrl = "https://placehold.co/600x400?text=Denim+Jacket",
                    CreatedAt = new DateTime(2024, 1, 4)
                },
                new Product
                {
                    Id = 11,
                    Name = "Wide Leg Trousers",
                    Description = "Comfortable wide leg trousers with a modern silhouette.",
                    Price = 95.00m,
                    Category = "Bottoms",
                    AvailableColors = new List<string> { "Black", "Beige", "Navy" },
                    AvailableSizes = new List<string> { "XS", "S", "M", "L", "XL" },
                    StockQuantity = 55,
                    ImageUrl = "https://placehold.co/600x400?text=Wide+Leg+Trousers",
                    CreatedAt = new DateTime(2024, 1, 4)
                },
                new Product
                {
                    Id = 12,
                    Name = "Cashmere Sweater",
                    Description = "Ultra-soft 100% cashmere sweater for ultimate comfort.",
                    Price = 159.00m,
                    Category = "Tops",
                    AvailableColors = new List<string> { "Cream", "Gray", "Black", "Burgundy" },
                    AvailableSizes = new List<string> { "S", "M", "L" },
                    StockQuantity = 20,
                    ImageUrl = "https://placehold.co/600x400?text=Cashmere+Sweater",
                    CreatedAt = new DateTime(2024, 1, 5)
                },
                new Product
                {
                    Id = 13,
                    Name = "Ankle Boots",
                    Description = "Stylish ankle boots with comfortable block heel.",
                    Price = 189.00m,
                    Category = "Footwear",
                    AvailableColors = new List<string> { "Black", "Brown", "Cognac" },
                    AvailableSizes = new List<string> { "36", "37", "38", "39", "40", "41" },
                    StockQuantity = 30,
                    ImageUrl = "https://placehold.co/600x400?text=Ankle+Boots",
                    CreatedAt = new DateTime(2024, 1, 5)
                },
                new Product
                {
                    Id = 14,
                    Name = "Oversized Blazer",
                    Description = "Trendy oversized blazer for a chic look.",
                    Price = 199.00m,
                    Category = "Outerwear",
                    AvailableColors = new List<string> { "Black", "Gray", "Beige" },
                    AvailableSizes = new List<string> { "S", "M", "L", "XL" },
                    StockQuantity = 25,
                    ImageUrl = "https://placehold.co/600x400?text=Oversized+Blazer",
                    CreatedAt = new DateTime(2024, 1, 6)
                },
                new Product
                {
                    Id = 15,
                    Name = "Pleated Midi Skirt",
                    Description = "Elegant pleated midi skirt for any occasion.",
                    Price = 75.00m,
                    Category = "Bottoms",
                    AvailableColors = new List<string> { "Black", "Navy", "Olive" },
                    AvailableSizes = new List<string> { "XS", "S", "M", "L" },
                    StockQuantity = 40,
                    ImageUrl = "https://placehold.co/600x400?text=Midi+Skirt",
                    CreatedAt = new DateTime(2024, 1, 6)
                },
                new Product
                {
                    Id = 16,
                    Name = "Canvas Backpack",
                    Description = "Durable canvas backpack with laptop compartment.",
                    Price = 69.00m,
                    Category = "Accessories",
                    AvailableColors = new List<string> { "Khaki", "Black", "Navy" },
                    AvailableSizes = new List<string> { "One Size" },
                    StockQuantity = 50,
                    ImageUrl = "https://placehold.co/600x400?text=Canvas+Backpack",
                    CreatedAt = new DateTime(2024, 1, 7)
                },
                new Product
                {
                    Id = 17,
                    Name = "Striped Polo Shirt",
                    Description = "Classic striped polo shirt for casual weekends.",
                    Price = 45.00m,
                    Category = "Tops",
                    AvailableColors = new List<string> { "Navy/White", "Red/White", "Green/White" },
                    AvailableSizes = new List<string> { "S", "M", "L", "XL", "XXL" },
                    StockQuantity = 60,
                    ImageUrl = "https://placehold.co/600x400?text=Polo+Shirt",
                    CreatedAt = new DateTime(2024, 1, 7)
                },
                new Product
                {
                    Id = 18,
                    Name = "Leather Belt",
                    Description = "Premium leather belt with silver buckle.",
                    Price = 55.00m,
                    Category = "Accessories",
                    AvailableColors = new List<string> { "Black", "Brown" },
                    AvailableSizes = new List<string> { "S", "M", "L", "XL" },
                    StockQuantity = 80,
                    ImageUrl = "https://placehold.co/600x400?text=Leather+Belt",
                    CreatedAt = new DateTime(2024, 1, 8)
                },
                new Product
                {
                    Id = 19,
                    Name = "Wrap Maxi Dress",
                    Description = "Flowing wrap maxi dress perfect for evening events.",
                    Price = 129.00m,
                    Category = "Dresses",
                    AvailableColors = new List<string> { "Burgundy", "Navy", "Emerald" },
                    AvailableSizes = new List<string> { "XS", "S", "M", "L" },
                    StockQuantity = 20,
                    ImageUrl = "https://placehold.co/600x400?text=Maxi+Dress",
                    CreatedAt = new DateTime(2024, 1, 8)
                },
                new Product
                {
                    Id = 20,
                    Name = "Athletic Joggers",
                    Description = "Comfortable athletic joggers for workouts or lounging.",
                    Price = 65.00m,
                    Category = "Bottoms",
                    AvailableColors = new List<string> { "Black", "Gray", "Navy" },
                    AvailableSizes = new List<string> { "S", "M", "L", "XL" },
                    StockQuantity = 70,
                    ImageUrl = "https://placehold.co/600x400?text=Athletic+Joggers",
                    CreatedAt = new DateTime(2024, 1, 9)
                }
            );
        }
    }
}
