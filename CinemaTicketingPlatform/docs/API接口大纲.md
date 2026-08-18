# API 接口大纲（v1）

> 基础路径：/api/v1
> 认证：Authorization: Bearer <JWT>
> 统一响应：`{ "code": 0, "message": "ok", "data": ... }`（错误时 code 非 0）
> 分页：page、page_size，响应含 total
> 详细字段以 FastAPI /docs 为准，本文件用于前后端对齐

## 错误码约定

| code | 含义 |
|---|---|
| 0 | 成功 |
| 4000 | 业务冲突（座位已占、票数超限、转赠违规等） |
| 401 | 未认证 |
| 4011 | 登录失败 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 排片冲突 |
| 422 | 参数校验失败 |
| 500 | 系统错误 |

## 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /auth/register | 注册（username/password/nickname） |
| POST | /auth/login | 登录，返回 access_token |
| GET | /auth/me | 当前用户信息 |

## 电影

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /movies | 电影列表（分页，可按标题搜索） |
| GET | /movies/{id} | 电影详情 + 近期场次 |
| POST | /movies | 新增电影（admin） |
| PUT | /movies/{id} | 修改电影（admin） |
| DELETE | /movies/{id} | 删除电影（admin，有场次禁止） |

## 场馆

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /venues | 场馆列表 |
| GET | /venues/{id} | 场馆详情（含模板信息） |
| POST | /venues | 新建场馆（admin：行列数/容量/出入口/荧幕位置） |
| PUT | /venues/{id} | 修改场馆基础信息（admin，有未来场次受限） |
| GET | /venues/{id}/seats | 场馆座位模板 |
| PUT | /venues/{id}/seats | 批量启用/禁用模板座位（admin） |

## 场次

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /sessions | 场次列表（按电影/场馆/日期筛选，含余票） |
| GET | /sessions/{id} | 场次详情（含票价、开停售时间、状态） |
| GET | /sessions/{id}/seats | 座位图（AVAILABLE/LOCKED/SOLD/DISABLED） |
| POST | /sessions | 排片（admin；冲突检测含 30 分钟缓冲） |
| PUT | /sessions/{id} | 改场次（admin；仅未来且无订单） |
| DELETE | /sessions/{id} | 删场次（admin；有订单禁止） |

## 订单与选座

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /orders | 创建订单：{session_id, seat_ids}；锁座并校验规则 |
| GET | /orders | 我的订单列表（分页） |
| GET | /orders/{id} | 订单详情（含票） |
| POST | /orders/{id}/pay | 发起支付（mock 立即成功；沙箱返回跳转参数） |
| POST | /orders/{id}/sync-payment | 主动查询支付状态并同步订单（本地无公网回调时的兜底） |
| POST | /orders/{id}/cancel | 取消待支付订单（释放座位） |

## 支付回调

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /payments/{trade_no}/callback | 支付宝异步回调（验签 + 幂等） |

## 票

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /tickets | 我的票（status 筛选：PENDING_PAYMENT/UNUSED/USED/REFUNDED/EXPIRED） |
| GET | /tickets/{id} | 票详情（含倒计时、自购/受赠标签） |
| POST | /tickets/{id}/transfer | 转赠：{to_user_id} |
| POST | /tickets/{id}/refund-request | 申请退款：{reason} |

## 退款审核（admin）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /admin/refund-requests | 退款申请列表（按状态筛选） |
| POST | /admin/refund-requests/{id}/approve | 同意（扣 10% 手续费，座位回待售） |
| POST | /admin/refund-requests/{id}/reject | 拒绝 |

## 核销（admin）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /admin/tickets/{id}/checkin | 单票核销 |
| POST | /admin/sessions/{id}/checkin | 整场一键核销 |

## 管理统计（admin，可选）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /admin/stats | 概览：票房、场次数、售出/核销数 |
| GET | /admin/sessions/{id}/tickets | 场次票务明细（含核销状态） |

## 状态枚举

- 座位：AVAILABLE / LOCKED / SOLD / DISABLED
- 票：PENDING_PAYMENT / UNUSED / USED / REFUND_APPLIED / REFUNDED / EXPIRED
- 订单：PENDING_PAYMENT / PAID / EXPIRED / CANCELLED
- 退款申请：PENDING / APPROVED / REJECTED
- 场次：SCHEDULED / SELLING / STOPPED / ENDED / CANCELLED（字段推导 + 状态冗余）
