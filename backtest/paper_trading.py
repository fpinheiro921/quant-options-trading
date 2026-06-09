"""
Paper Trading / Sandbox Environment for Strategy Backtesting.

Simulates trades without real money at risk. Tracks performance as if
executing in a live account, but with simulated fills and P&L.

Features:
- Simulated order execution with realistic slippage
- Paper account balance tracking
- Trade history logging
- Performance metrics calculation
- Transition path to live trading
"""
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import pickle
import os

logger = logging.getLogger(__name__)


class TradeType(Enum):
    STOCK = "stock"
    OPTION = "option"


class TradeAction(Enum):
    BUY = "buy"
    SELL = "sell"
    BUY_TO_OPEN = "buy_to_open"
    SELL_TO_OPEN = "sell_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_CLOSE = "sell_to_close"


@dataclass
class PaperTrade:
    """A simulated trade record."""
    trade_id: str
    timestamp: datetime
    symbol: str
    trade_type: TradeType
    action: TradeAction
    quantity: int
    entry_price: float
    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    
    # Option-specific
    option_strike: Optional[float] = None
    option_expiry: Optional[datetime] = None
    option_type: Optional[str] = None  # 'call' or 'put'
    
    # P&L tracking
    realized_pnl: float = 0.0
    fees: float = 0.0
    
    # Metadata
    strategy: str = ""  # 'wheel' or 'momentum'
    notes: str = ""
    
    @property
    def is_open(self) -> bool:
        return self.exit_price is None
    
    @property
    def duration_days(self) -> float:
        if self.exit_timestamp:
            return (self.exit_timestamp - self.timestamp).total_seconds() / 86400
        return (datetime.now() - self.timestamp).total_seconds() / 86400
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trade_id': self.trade_id,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'trade_type': self.trade_type.value,
            'action': self.action.value,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'exit_timestamp': self.exit_timestamp.isoformat() if self.exit_timestamp else None,
            'option_strike': self.option_strike,
            'option_expiry': self.option_expiry.isoformat() if self.option_expiry else None,
            'option_type': self.option_type,
            'realized_pnl': self.realized_pnl,
            'fees': self.fees,
            'strategy': self.strategy,
            'notes': self.notes,
            'is_open': self.is_open,
            'duration_days': self.duration_days,
        }


@dataclass
class PaperPosition:
    """A simulated open position."""
    symbol: str
    quantity: int
    average_cost: float
    trade_type: TradeType
    opened_at: datetime
    
    # For options
    option_strike: Optional[float] = None
    option_expiry: Optional[datetime] = None
    option_type: Optional[str] = None
    
    def market_value(self, current_price: float) -> float:
        return self.quantity * current_price
    
    def unrealized_pnl(self, current_price: float) -> float:
        return self.quantity * (current_price - self.average_cost)


@dataclass
class PaperAccount:
    """Paper trading account state."""
    cash_balance: float = 100000.0  # Start with $100k default
    initial_balance: float = 100000.0
    
    # Track values
    total_deposits: float = 0.0
    total_withdrawals: float = 0.0
    total_fees: float = 0.0
    
    # History
    trades: List[PaperTrade] = field(default_factory=list)
    positions: Dict[str, PaperPosition] = field(default_factory=dict)
    
    def total_value(self, market_prices: Dict[str, float]) -> float:
        """Calculate total account value including positions."""
        positions_value = sum(
            pos.market_value(market_prices.get(symbol, pos.average_cost))
            for symbol, pos in self.positions.items()
        )
        return self.cash_balance + positions_value
    
    def realized_pnl(self) -> float:
        """Total realized P&L from closed trades."""
        return sum(t.realized_pnl for t in self.trades if not t.is_open)
    
    def win_rate(self) -> float:
        """Percentage of winning trades."""
        closed = [t for t in self.trades if not t.is_open]
        if not closed:
            return 0.0
        winners = sum(1 for t in closed if t.realized_pnl > 0)
        return winners / len(closed)
    
    def to_dict(self, market_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        return {
            'cash_balance': round(self.cash_balance, 2),
            'initial_balance': round(self.initial_balance, 2),
            'total_value': round(self.total_value(market_prices or {}), 2),
            'realized_pnl': round(self.realized_pnl(), 2),
            'total_return_pct': round((self.realized_pnl() / self.initial_balance) * 100, 2),
            'win_rate': round(self.win_rate(), 4),
            'total_trades': len(self.trades),
            'open_positions': len(self.positions),
            'total_fees': round(self.total_fees, 2),
        }


class PaperTradingEnvironment:
    """
    Paper trading environment for safe strategy testing.
    
    Simulates:
    - Order fills with realistic slippage
    - Commission fees ($0.50/contract for options)
    - Account balance updates
    - Position tracking
    - Trade history
    """
    
    # Fee structure (TastyTrade-like)
    OPTION_FEE_PER_CONTRACT = 0.50  # $0.50 per option contract
    STOCK_FEE_PER_SHARE = 0.0  # Free stock trades on TastyTrade
    SLIPPAGE_PCT = 0.001  # 0.1% slippage on fills
    
    def __init__(self, starting_balance: float = 100000.0, load_from_file: Optional[str] = None):
        """
        Initialize paper trading environment.
        
        Args:
            starting_balance: Initial cash balance (default $100,000)
            load_from_file: Path to saved paper account state (optional)
        """
        if load_from_file and os.path.exists(load_from_file):
            with open(load_from_file, 'rb') as f:
                self.account = pickle.load(f)
            logger.info(f"Loaded paper account from {load_from_file}")
        else:
            self.account = PaperAccount(
                cash_balance=starting_balance,
                initial_balance=starting_balance
            )
            logger.info(f"Created new paper account with ${starting_balance:,.2f}")
        
        self.save_file = load_from_file or "paper_account.pkl"
        self._trade_counter = len(self.account.trades)
    
    def _generate_trade_id(self) -> str:
        """Generate unique trade ID."""
        self._trade_counter += 1
        return f"PAPER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._trade_counter:04d}"
    
    def _calculate_slippage(self, price: float, action: TradeAction) -> float:
        """Apply realistic slippage to price."""
        # Buy fills higher, sell fills lower
        if action in [TradeAction.BUY, TradeAction.BUY_TO_OPEN, TradeAction.BUY_TO_CLOSE]:
            return price * (1 + self.SLIPPAGE_PCT)
        else:
            return price * (1 - self.SLIPPAGE_PCT)
    
    def _calculate_fees(
        self,
        quantity: int,
        trade_type: TradeType
    ) -> float:
        """Calculate trading fees."""
        if trade_type == TradeType.OPTION:
            return quantity * self.OPTION_FEE_PER_CONTRACT
        return 0.0  # Free stock trades
    
    def execute_stock_trade(
        self,
        symbol: str,
        quantity: int,
        action: TradeAction,
        market_price: float,
        timestamp: Optional[datetime] = None,
        strategy: str = ""
    ) -> Optional[PaperTrade]:
        """
        Execute a simulated stock trade.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: Buy or sell
            market_price: Current market price
            timestamp: Trade timestamp (default: now)
            strategy: Strategy name for tracking
            
        Returns:
            PaperTrade if executed successfully, None if failed
        """
        timestamp = timestamp or datetime.now()
        
        # Apply slippage
        fill_price = self._calculate_slippage(market_price, action)
        
        # Calculate costs
        notional = quantity * fill_price
        fees = self._calculate_fees(quantity, TradeType.STOCK)
        
        if action == TradeAction.BUY:
            # Check if enough cash
            total_cost = notional + fees
            if total_cost > self.account.cash_balance:
                logger.warning(f"Insufficient cash for {symbol} purchase: ${total_cost:.2f} needed, ${self.account.cash_balance:.2f} available")
                return None
            
            # Update cash
            self.account.cash_balance -= total_cost
            
            # Update or create position
            if symbol in self.account.positions:
                pos = self.account.positions[symbol]
                # Average cost basis
                total_cost_basis = (pos.quantity * pos.average_cost) + (quantity * fill_price)
                pos.quantity += quantity
                pos.average_cost = total_cost_basis / pos.quantity
            else:
                self.account.positions[symbol] = PaperPosition(
                    symbol=symbol,
                    quantity=quantity,
                    average_cost=fill_price,
                    trade_type=TradeType.STOCK,
                    opened_at=timestamp
                )
        
        else:  # SELL
            # Check if position exists
            if symbol not in self.account.positions:
                logger.warning(f"Cannot sell {symbol} - no position exists")
                return None
            
            pos = self.account.positions[symbol]
            if quantity > pos.quantity:
                logger.warning(f"Cannot sell {quantity} shares of {symbol} - only have {pos.quantity}")
                return None
            
            # Calculate P&L
            realized_pnl = quantity * (fill_price - pos.average_cost) - fees
            
            # Update cash
            self.account.cash_balance += (notional - fees)
            
            # Update position
            pos.quantity -= quantity
            if pos.quantity == 0:
                del self.account.positions[symbol]
            
            # Record the P&L
            self.account.total_fees += fees
            
            # Create completed trade record
            trade = PaperTrade(
                trade_id=self._generate_trade_id(),
                timestamp=pos.opened_at,  # Original entry time
                symbol=symbol,
                trade_type=TradeType.STOCK,
                action=action,
                quantity=quantity,
                entry_price=pos.average_cost,
                exit_price=fill_price,
                exit_timestamp=timestamp,
                realized_pnl=realized_pnl,
                fees=fees,
                strategy=strategy
            )
            self.account.trades.append(trade)
            
            logger.info(f"Paper SELL {symbol}: {quantity} @ ${fill_price:.2f}, P&L: ${realized_pnl:.2f}")
            return trade
        
        # For BUY, create an open trade (will be closed later)
        trade = PaperTrade(
            trade_id=self._generate_trade_id(),
            timestamp=timestamp,
            symbol=symbol,
            trade_type=TradeType.STOCK,
            action=action,
            quantity=quantity,
            entry_price=fill_price,
            fees=fees,
            strategy=strategy
        )
        self.account.trades.append(trade)
        
        logger.info(f"Paper BUY {symbol}: {quantity} @ ${fill_price:.2f}, Fees: ${fees:.2f}")
        return trade
    
    def execute_option_trade(
        self,
        symbol: str,
        option_symbol: str,
        quantity: int,
        action: TradeAction,
        market_price: float,
        strike: float,
        expiry: datetime,
        option_type: str,  # 'call' or 'put'
        timestamp: Optional[datetime] = None,
        strategy: str = ""
    ) -> Optional[PaperTrade]:
        """
        Execute a simulated option trade.
        
        Args:
            symbol: Underlying stock symbol
            option_symbol: Full option symbol
            quantity: Number of contracts (each = 100 shares)
            action: Buy or sell (to open/close)
            market_price: Option premium price
            strike: Strike price
            expiry: Expiration date
            option_type: 'call' or 'put'
            timestamp: Trade timestamp
            strategy: Strategy name
            
        Returns:
            PaperTrade if executed, None if failed
        """
        timestamp = timestamp or datetime.now()
        
        # Apply slippage
        fill_price = self._calculate_slippage(market_price, action)
        
        # Calculate costs (options are per contract, 1 contract = 100 shares)
        notional = quantity * 100 * fill_price
        fees = self._calculate_fees(quantity, TradeType.OPTION)
        
        # For SELL_TO_OPEN (short options), calculate margin/cash requirement
        if action == TradeAction.SELL_TO_OPEN:
            if option_type == 'call':
                # Covered call - need stock position
                if symbol not in self.account.positions:
                    logger.warning(f"Cannot sell covered call on {symbol} - no stock position")
                    return None
                stock_pos = self.account.positions[symbol]
                if stock_pos.quantity < quantity * 100:
                    logger.warning(f"Not enough shares for {quantity} contracts")
                    return None
            
            elif option_type == 'put':
                # Cash-secured put - need cash for assignment
                cash_required = quantity * 100 * strike
                if cash_required > self.account.cash_balance:
                    logger.warning(f"Insufficient cash for cash-secured put: ${cash_required:.2f} needed")
                    return None
        
        # Execute trade logic (simplified for paper trading)
        if action in [TradeAction.BUY_TO_OPEN, TradeAction.SELL_TO_OPEN]:
            # Opening position
            total_cost = notional + fees if action == TradeAction.BUY_TO_OPEN else fees
            
            if action == TradeAction.BUY_TO_OPEN:
                if total_cost > self.account.cash_balance:
                    logger.warning(f"Insufficient cash for option purchase")
                    return None
                self.account.cash_balance -= total_cost
            else:  # SELL_TO_OPEN - collect premium
                self.account.cash_balance += (notional - fees)
            
            # Create open trade
            trade = PaperTrade(
                trade_id=self._generate_trade_id(),
                timestamp=timestamp,
                symbol=option_symbol,
                trade_type=TradeType.OPTION,
                action=action,
                quantity=quantity,
                entry_price=fill_price,
                option_strike=strike,
                option_expiry=expiry,
                option_type=option_type,
                fees=fees,
                strategy=strategy,
                notes=f"Underlying: {symbol}"
            )
            self.account.trades.append(trade)
            
            # Track open option position
            self.account.positions[option_symbol] = PaperPosition(
                symbol=option_symbol,
                quantity=quantity if action == TradeAction.BUY_TO_OPEN else -quantity,
                average_cost=fill_price,
                trade_type=TradeType.OPTION,
                opened_at=timestamp,
                option_strike=strike,
                option_expiry=expiry,
                option_type=option_type
            )
            
            logger.info(f"Paper {action.value.upper()} {option_symbol}: {quantity} @ ${fill_price:.2f}")
            return trade
        
        else:  # Closing positions (BUY_TO_CLOSE or SELL_TO_CLOSE)
            # Find matching open position
            if option_symbol not in self.account.positions:
                logger.warning(f"No open position for {option_symbol}")
                return None
            
            pos = self.account.positions[option_symbol]
            
            # Calculate P&L
            if action == TradeAction.BUY_TO_CLOSE:  # Closing short position
                realized_pnl = pos.quantity * 100 * (pos.average_cost - fill_price) - fees
            else:  # SELL_TO_CLOSE - Closing long position
                realized_pnl = quantity * 100 * (fill_price - pos.average_cost) - fees
            
            # Update cash
            if action == TradeAction.BUY_TO_CLOSE:
                self.account.cash_balance -= (notional + fees)
            else:
                self.account.cash_balance += (notional - fees)
            
            # Close position
            del self.account.positions[option_symbol]
            
            # Create completed trade
            trade = PaperTrade(
                trade_id=self._generate_trade_id(),
                timestamp=pos.opened_at,
                symbol=option_symbol,
                trade_type=TradeType.OPTION,
                action=action,
                quantity=quantity,
                entry_price=pos.average_cost,
                exit_price=fill_price,
                exit_timestamp=timestamp,
                option_strike=strike,
                option_expiry=expiry,
                option_type=option_type,
                realized_pnl=realized_pnl,
                fees=fees,
                strategy=strategy
            )
            self.account.trades.append(trade)
            
            logger.info(f"Paper CLOSE {option_symbol}: P&L ${realized_pnl:.2f}")
            return trade
    
    def get_account_summary(self, market_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Get paper account summary."""
        return self.account.to_dict(market_prices)
    
    def get_open_trades(self) -> List[PaperTrade]:
        """Get list of open trades."""
        return [t for t in self.account.trades if t.is_open]
    
    def get_closed_trades(self) -> List[PaperTrade]:
        """Get list of closed trades."""
        return [t for t in self.account.trades if not t.is_open]
    
    def save_state(self, filepath: Optional[str] = None):
        """Save paper account state to file."""
        filepath = filepath or self.save_file
        with open(filepath, 'wb') as f:
            pickle.dump(self.account, f)
        logger.info(f"Saved paper account state to {filepath}")
    
    def reset_account(self, new_balance: float = 100000.0):
        """Reset paper account to initial state."""
        self.account = PaperAccount(
            cash_balance=new_balance,
            initial_balance=new_balance
        )
        self._trade_counter = 0
        logger.info(f"Reset paper account with ${new_balance:,.2f}")
    
    def simulate_option_assignment(
        self,
        option_symbol: str,
        stock_price: float,
        timestamp: Optional[datetime] = None
    ) -> Optional[PaperTrade]:
        """
        Simulate option assignment (for wheel strategy testing).
        
        This simulates what happens when:
        - Short call is ITM at expiry (sell stock at strike)
        - Short put is ITM at expiry (buy stock at strike)
        """
        timestamp = timestamp or datetime.now()
        
        if option_symbol not in self.account.positions:
            logger.warning(f"No position for {option_symbol}")
            return None
        
        pos = self.account.positions[option_symbol]
        
        if pos.trade_type != TradeType.OPTION or pos.quantity >= 0:
            logger.warning(f"Cannot assign - not a short option position")
            return None
        
        # Determine assignment outcome based on option type
        if pos.option_type == 'call':
            # Short call assigned = sell stock at strike
            # Need to have stock position
            underlying = option_symbol.split()[0] if ' ' in option_symbol else option_symbol[:4]
            
            if underlying not in self.account.positions:
                logger.warning(f"Cannot assign call - no {underlying} position")
                return None
            
            stock_pos = self.account.positions[underlying]
            contracts = abs(pos.quantity)
            shares_needed = contracts * 100
            
            if stock_pos.quantity < shares_needed:
                logger.warning(f"Not enough shares for assignment")
                return None
            
            # Execute assignment
            strike = pos.option_strike
            realized_pnl = shares_needed * (strike - stock_pos.average_cost)
            
            # Update positions
            self.account.cash_balance += shares_needed * strike
            stock_pos.quantity -= shares_needed
            
            if stock_pos.quantity == 0:
                del self.account.positions[underlying]
            
            # Close option position
            del self.account.positions[option_symbol]
            
            logger.info(f"Call assigned: Sold {shares_needed} shares of {underlying} @ ${strike}")
            
            return PaperTrade(
                trade_id=self._generate_trade_id(),
                timestamp=pos.opened_at,
                symbol=option_symbol,
                trade_type=TradeType.OPTION,
                action=TradeAction.BUY_TO_CLOSE,
                quantity=contracts,
                entry_price=pos.average_cost,
                exit_price=0,
                exit_timestamp=timestamp,
                realized_pnl=realized_pnl,
                strategy="wheel",
                notes=f"Assignment: Sold {underlying} at ${strike}"
            )
        
        else:  # Put assignment
            # Short put assigned = buy stock at strike
            underlying = option_symbol.split()[0] if ' ' in option_symbol else option_symbol[:4]
            contracts = abs(pos.quantity)
            shares_to_buy = contracts * 100
            strike = pos.option_strike
            
            total_cost = shares_to_buy * strike
            
            if total_cost > self.account.cash_balance:
                logger.warning(f"Insufficient cash for put assignment: ${total_cost:.2f}")
                return None
            
            # Execute assignment
            self.account.cash_balance -= total_cost
            
            # Create or update stock position
            if underlying in self.account.positions:
                stock_pos = self.account.positions[underlying]
                total_shares = stock_pos.quantity + shares_to_buy
                total_cost_basis = (stock_pos.quantity * stock_pos.average_cost) + total_cost
                stock_pos.quantity = total_shares
                stock_pos.average_cost = total_cost_basis / total_shares
            else:
                self.account.positions[underlying] = PaperPosition(
                    symbol=underlying,
                    quantity=shares_to_buy,
                    average_cost=strike,
                    trade_type=TradeType.STOCK,
                    opened_at=timestamp
                )
            
            # Close option position
            del self.account.positions[option_symbol]
            
            logger.info(f"Put assigned: Bought {shares_to_buy} shares of {underlying} @ ${strike}")
            
            return PaperTrade(
                trade_id=self._generate_trade_id(),
                timestamp=pos.opened_at,
                symbol=option_symbol,
                trade_type=TradeType.OPTION,
                action=TradeAction.BUY_TO_CLOSE,
                quantity=contracts,
                entry_price=pos.average_cost,
                exit_price=0,
                exit_timestamp=timestamp,
                realized_pnl=pos.average_cost * shares_to_buy,  # Premium received
                strategy="wheel",
                notes=f"Assignment: Bought {underlying} at ${strike}"
            )


def create_paper_environment(starting_balance: float = 100000.0) -> PaperTradingEnvironment:
    """Factory function to create paper trading environment."""
    return PaperTradingEnvironment(starting_balance=starting_balance)
