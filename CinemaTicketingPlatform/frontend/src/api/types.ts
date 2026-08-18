export interface User {
  id: number;
  username: string;
  nickname: string;
  role: string;
  created_at: string;
}

export interface Movie {
  id: number;
  title: string;
  poster_url: string | null;
  duration_min: number;
  description: string | null;
  created_at: string;
}

export interface Venue {
  id: number;
  name: string;
  rows: number;
  cols: number;
  capacity: number;
  screen_pos: Record<string, unknown> | null;
  exits: Array<Record<string, string>> | null;
  status: string;
  created_at: string;
}

export interface VenueSeat {
  id: number;
  venue_id: number;
  row_no: number;
  col_no: number;
  seat_no: string;
  enabled: boolean;
}

export interface SessionItem {
  id: number;
  movie_id: number;
  venue_id: number;
  movie_title: string;
  venue_name: string;
  start_at: string;
  end_at: string;
  sale_open_at: string;
  sale_close_at: string;
  base_price: string;
  status: string;
  remaining: number;
  sold: number;
  locked: number;
  total_seats: number;
}

export interface SessionSeat {
  id: number;
  session_id: number;
  row_no: number;
  col_no: number;
  seat_no: string;
  price: string;
  status: string;
}

export interface Ticket {
  id: number;
  order_id: number;
  session_id: number;
  movie_title: string;
  venue_name: string;
  start_at: string;
  seat_no: string;
  row_no: number;
  col_no: number;
  price: string;
  status: string;
  origin: string;
  transfer_count: number;
  expires_at: string | null;
  checked_in_at: string | null;
  transferred_out?: boolean;
  transferred_to?: string | null;
}

export interface Payment {
  id: number;
  order_id: number;
  method: string;
  provider_trade_no: string;
  status: string;
  amount: string;
  pay_url: string | null;
  created_at: string;
  paid_at: string | null;
}

export interface Order {
  id: number;
  order_no: string;
  session_id: number;
  status: string;
  total_amount: string;
  created_at: string;
  paid_at: string | null;
  tickets: Ticket[];
  payments: Payment[];
}

export interface RefundRequest {
  id: number;
  ticket_id: number;
  seat_no: string;
  movie_title: string;
  venue_name: string;
  start_at: string;
  original_amount: string;
  refund_amount: string;
  fee: string;
  status: string;
  reason: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface TicketAdminOut {
  id: number;
  seat_no: string;
  price: string;
  status: string;
  origin: string;
  owner_username: string;
  purchaser_username: string;
  checked_in_at: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface SetupStatus {
  db_configured: boolean;
  alipay_configured: boolean;
  pay_provider: string;
  mysql_running: boolean;
}
