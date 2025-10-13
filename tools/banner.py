from pictex import Canvas, Column, Row, Text

canvas = Canvas()

composition = (
    Row(Column(Text("ib").color("#d90a1c")), Column(Text("auth").color("black")))
    .font_family("Roboto")
    .font_size(480)
    .size(1800, 600)
    .padding(0, 50)
)

image = canvas.render(composition)

image.save("ibauth-banner.png")
