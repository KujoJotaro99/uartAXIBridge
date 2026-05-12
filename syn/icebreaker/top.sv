// Top-level design file for the icebreaker FPGA board
module top
  (input [0:0] clk_12mhz_i
  // n: Negative Polarity (0 when pressed, 1 otherwise)
  // async: Not synchronized to clock
  // unsafe: Not De-Bounced
  ,input [0:0] reset_n_async_unsafe_i
  // async: Not synchronized to clock
  // unsafe: Not De-Bounced
  ,input [3:1] button_async_unsafe_i

  // Line Out (Green)
  // Main clock (for synchronization)
  ,output tx_main_clk_o
  // Selects between L/R channels, but called a "clock"
  ,output tx_lr_clk_o
  // Data clock
  ,output tx_data_clk_o
  // Output Data
  ,output tx_data_o

  // Line In (Blue)
  // Main clock (for synchronization)
  ,output rx_main_clk_o
  // Selects between L/R channels, but called a "clock"
  ,output rx_lr_clk_o
  // Data clock
  ,output rx_data_clk_o
  // Input data
  ,input  rx_data_i

  // Serial Interface
  ,input rx_serial_i
  // Input data
  ,output tx_serial_o

  ,output [5:1] led_o);

   reg reset_n_sync_r;
   reg reset_r;
   wire [3:0] buttons_r;

   assign buttons_r = {1'b0, ~button_async_unsafe_i};
   assign tx_main_clk_o = 1'b0;
   assign tx_lr_clk_o = 1'b0;
   assign tx_data_clk_o = 1'b0;
   assign tx_data_o = 1'b0;
   assign rx_main_clk_o = 1'b0;
   assign rx_lr_clk_o = 1'b0;
   assign rx_data_clk_o = 1'b0;

   always_ff @(posedge clk_12mhz_i) begin
      reset_n_sync_r <= reset_n_async_unsafe_i;
      reset_r <= ~reset_n_sync_r;
   end

   uart_axi
     uart_axi_i
       (/*autoinst*/
        // Outputs
        .tx_serial_o                    (tx_serial_o[0:0]),
        .led_o                          (led_o[5:1]),
        // Inputs
        .clk_i                          (clk_12mhz_i[0:0]),
        .reset_i                        (reset_r[0:0]),
        .rx_serial_i                    (rx_serial_i[0:0]),
        .buttons_i                      (buttons_r[3:0]));
                         
endmodule
