using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Outfitly.Migrations
{
    /// <inheritdoc />
    public partial class OverhaulProducts : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "ImageUrl",
                table: "Products");

            migrationBuilder.DropColumn(
                name: "StockQuantity",
                table: "Products");

            migrationBuilder.RenameColumn(
                name: "AvailableSizes",
                table: "Products",
                newName: "ImageUrls");

            migrationBuilder.CreateTable(
                name: "ProductSizes",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    ProductId = table.Column<int>(type: "int", nullable: false),
                    Size = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    Quantity = table.Column<int>(type: "int", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ProductSizes", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ProductSizes_Products_ProductId",
                        column: x => x.ProductId,
                        principalTable: "Products",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 1,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=White+Tee");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 2,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Jeans");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 3,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Jacket");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 4,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Sneakers");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 5,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Summer+Dress");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 6,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Linen+Pants");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 7,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Crossbody+Bag");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 8,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Wool+Coat");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 9,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Silk+Blouse");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 10,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Denim+Jacket");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 11,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Wide+Leg+Trousers");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 12,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Cashmere+Sweater");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 13,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Ankle+Boots");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 14,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Oversized+Blazer");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 15,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Midi+Skirt");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 16,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Canvas+Backpack");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 17,
                columns: new[] { "AvailableColors", "ImageUrls" },
                values: new object[] { "Navy,Red,Green", "https://placehold.co/600x400?text=Polo+Shirt" });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 18,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Leather+Belt");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 19,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Maxi+Dress");

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 20,
                column: "ImageUrls",
                value: "https://placehold.co/600x400?text=Athletic+Joggers");

            migrationBuilder.CreateIndex(
                name: "IX_ProductSizes_ProductId",
                table: "ProductSizes",
                column: "ProductId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "ProductSizes");

            migrationBuilder.RenameColumn(
                name: "ImageUrls",
                table: "Products",
                newName: "AvailableSizes");

            migrationBuilder.AddColumn<string>(
                name: "ImageUrl",
                table: "Products",
                type: "nvarchar(max)",
                nullable: true);

            migrationBuilder.AddColumn<int>(
                name: "StockQuantity",
                table: "Products",
                type: "int",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 1,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "S,M,L,XL", "https://placehold.co/600x400?text=White+Tee", 100 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 2,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "30,32,34,36", "https://placehold.co/600x400?text=Jeans", 50 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 3,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "M,L,XL", "https://placehold.co/600x400?text=Jacket", 30 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 4,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "8,9,10,11", "https://placehold.co/600x400?text=Sneakers", 40 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 5,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "XS,S,M", "https://placehold.co/600x400?text=Summer+Dress", 25 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 6,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "S,M,L,XL", "https://placehold.co/600x400?text=Linen+Pants", 45 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 7,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "One Size", "https://placehold.co/600x400?text=Crossbody+Bag", 20 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 8,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "S,M,L", "https://placehold.co/600x400?text=Wool+Coat", 15 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 9,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "XS,S,M,L", "https://placehold.co/600x400?text=Silk+Blouse", 35 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 10,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "S,M,L,XL", "https://placehold.co/600x400?text=Denim+Jacket", 40 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 11,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "XS,S,M,L,XL", "https://placehold.co/600x400?text=Wide+Leg+Trousers", 55 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 12,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "S,M,L", "https://placehold.co/600x400?text=Cashmere+Sweater", 20 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 13,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "36,37,38,39,40,41", "https://placehold.co/600x400?text=Ankle+Boots", 30 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 14,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "S,M,L,XL", "https://placehold.co/600x400?text=Oversized+Blazer", 25 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 15,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "XS,S,M,L", "https://placehold.co/600x400?text=Midi+Skirt", 40 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 16,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "One Size", "https://placehold.co/600x400?text=Canvas+Backpack", 50 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 17,
                columns: new[] { "AvailableColors", "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "Navy/White,Red/White,Green/White", "S,M,L,XL,XXL", "https://placehold.co/600x400?text=Polo+Shirt", 60 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 18,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "S,M,L,XL", "https://placehold.co/600x400?text=Leather+Belt", 80 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 19,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "XS,S,M,L", "https://placehold.co/600x400?text=Maxi+Dress", 20 });

            migrationBuilder.UpdateData(
                table: "Products",
                keyColumn: "Id",
                keyValue: 20,
                columns: new[] { "AvailableSizes", "ImageUrl", "StockQuantity" },
                values: new object[] { "S,M,L,XL", "https://placehold.co/600x400?text=Athletic+Joggers", 70 });
        }
    }
}
