library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity Adder is
  port (
    clk : in std_logic;
    value_a : in unsigned(7 downto 0);
    value_b : in unsigned(7 downto 0);
    result : out unsigned(8 downto 0)
  );
end Adder;

architecture arch_Adder of Adder is
begin
  process(clk)
  begin
    if rising_edge(clk) then
      result <= resize(value_a, 9) + value_b;
    end if;
  end process;
end architecture arch_Adder;
