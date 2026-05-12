module uart_axi
  #(parameter example_p = 0) // Does nothing, just an example. You may use it, extend it, or ignore it.
  (input [0:0] clk_i // 12 MHz clock
  ,input [0:0] reset_i

  ,input [0:0] rx_serial_i
  ,output [0:0] tx_serial_o

  ,input [3:0] buttons_i // Read these
  ,output [5:1] led_o // Turn these on/off
  );

  // master to slave
  wire mem_awvalid;
  wire [31:0] mem_awaddr;
  wire [3:0] mem_awid;
  wire [7:0] mem_awlen;
  wire [1:0] mem_awburst;

  wire mem_wvalid;
  wire [31:0] mem_wdata;
  wire [3:0] mem_wstrb;
  wire mem_wlast;

  wire mem_bready;

  wire mem_arvalid;
  wire [31:0] mem_araddr;
  wire [3:0] mem_arid;
  wire [7:0] mem_arlen;
  wire [1:0] mem_arburst;

  wire mem_rready;

  // slave to master
  wire mem_awready;
  wire mem_wready;
  wire mem_bvalid;
  wire [1:0] mem_bresp;
  wire [3:0] mem_bid;

  wire mem_arready;
  wire mem_rvalid;
  wire [31:0] mem_rdata;
  wire [1:0] mem_rresp;
  wire [3:0] mem_rid;
  wire mem_rlast;

  // gpio values
  wire [31:0] gpio_outputs;

  assign led_o = gpio_outputs[5:1];

  // master
  dbg_bridge 
  #(
    .CLK_FREQ(12000000),
    .UART_SPEED(3000000) // test baud for sim
  ) dbg_inst 
  (
    .clk_i(clk_i),
    .rst_i(reset_i),

    .uart_rxd_i(rx_serial_i),
    .uart_txd_o(tx_serial_o),

    // axi wraddr
    .mem_awvalid_o(mem_awvalid), // address valid
    .mem_awaddr_o(mem_awaddr), // address to write
    .mem_awid_o(mem_awid),
    .mem_awlen_o(mem_awlen),
    .mem_awburst_o(mem_awburst),

    // axi wrdata
    .mem_wvalid_o(mem_wvalid), // data valid
    .mem_wdata_o(mem_wdata), // data to write
    .mem_wstrb_o(mem_wstrb), // byte enables
    .mem_wlast_o(mem_wlast), // last beat of burst

    // axi wrresponse
    .mem_bready_o(mem_bready), // bridge accepts response

    // axi rdaddr
    .mem_arvalid_o(mem_arvalid),
    .mem_araddr_o(mem_araddr),
    .mem_arid_o(mem_arid),
    .mem_arlen_o(mem_arlen),
    .mem_arburst_o(mem_arburst),

    // axi rddata
    .mem_rready_o(mem_rready),

    // ram signal
    .mem_awready_i(mem_awready), // memory accepts address
    .mem_wready_i(mem_wready), // memory ready for data
    .mem_bvalid_i(mem_bvalid), // write completed
    .mem_bresp_i(mem_bresp), // error or not
    .mem_bid_i(mem_bid),

    .mem_arready_i(mem_arready),
    .mem_rvalid_i(mem_rvalid),
    .mem_rdata_i(mem_rdata),
    .mem_rresp_i(mem_rresp),
    .mem_rid_i(mem_rid),
    .mem_rlast_i(mem_rlast),

    // gpio
    .gpio_inputs_i({28'b0, buttons_i}),
    .gpio_outputs_o(gpio_outputs)
  );

  // slave
  axi_ram 
  #(
    .DATA_WIDTH(32),
    .ADDR_WIDTH(16), 
    .ID_WIDTH(4)
  ) ram_inst
  (
    .clk(clk_i),
    .rst(reset_i),

    .s_axi_awid(mem_awid),
    .s_axi_awaddr(mem_awaddr[15:0]),
    .s_axi_awlen(mem_awlen),
    .s_axi_awsize(3'b010),
    .s_axi_awburst(mem_awburst),
    .s_axi_awlock(1'b0),
    .s_axi_awcache(4'b0),
    .s_axi_awprot(3'b0),
    .s_axi_awvalid(mem_awvalid),
    .s_axi_awready(mem_awready),

    .s_axi_wdata(mem_wdata),
    .s_axi_wstrb(mem_wstrb),
    .s_axi_wlast(mem_wlast),
    .s_axi_wvalid(mem_wvalid),
    .s_axi_wready(mem_wready),

    .s_axi_bid(mem_bid),
    .s_axi_bresp(mem_bresp),
    .s_axi_bvalid(mem_bvalid),
    .s_axi_bready(mem_bready),

    .s_axi_arid(mem_arid),
    .s_axi_araddr(mem_araddr[15:0]),
    .s_axi_arlen(mem_arlen),
    .s_axi_arsize(3'b010),
    .s_axi_arburst(mem_arburst),
    .s_axi_arlock(1'b0),
    .s_axi_arcache(4'b0),
    .s_axi_arprot(3'b0),
    .s_axi_arvalid(mem_arvalid),
    .s_axi_arready(mem_arready),

    .s_axi_rid(mem_rid),
    .s_axi_rdata(mem_rdata),
    .s_axi_rresp(mem_rresp),
    .s_axi_rlast(mem_rlast),
    .s_axi_rvalid(mem_rvalid),
    .s_axi_rready(mem_rready)
  );


endmodule
