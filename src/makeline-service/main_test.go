package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

// mockOrderRepo is a test double for the OrderRepo interface.
type mockOrderRepo struct {
	pendingOrders []Order
	orders        map[string]Order
	insertErr     error
	updateErr     error
	getErr        error
	pendingErr    error
}

func (m *mockOrderRepo) GetPendingOrders() ([]Order, error) {
	if m.pendingErr != nil {
		return nil, m.pendingErr
	}
	return m.pendingOrders, nil
}

func (m *mockOrderRepo) GetOrder(id string) (Order, error) {
	if m.getErr != nil {
		return Order{}, m.getErr
	}
	order, ok := m.orders[id]
	if !ok {
		return Order{}, errors.New("order not found")
	}
	return order, nil
}

func (m *mockOrderRepo) InsertOrders(orders []Order) error {
	return m.insertErr
}

func (m *mockOrderRepo) UpdateOrder(order Order) error {
	return m.updateErr
}

// setupRouter creates a gin router with the given OrderService injected via middleware.
func setupRouter(svc *OrderService) *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.Use(OrderMiddleware(svc))
	r.GET("/order/:id", getOrder)
	r.PUT("/order", updateOrder)
	return r
}

// TestNewOrderService verifies that NewOrderService wires the repo correctly.
func TestNewOrderService(t *testing.T) {
	repo := &mockOrderRepo{}
	svc := NewOrderService(repo)
	if svc == nil {
		t.Fatal("expected non-nil OrderService")
	}
	if svc.repo != repo {
		t.Error("expected repo to be the one passed to NewOrderService")
	}
}

// TestOrderMiddleware verifies that the middleware sets the orderService key in context.
func TestOrderMiddleware(t *testing.T) {
	repo := &mockOrderRepo{}
	svc := NewOrderService(repo)

	var captured *OrderService
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.Use(OrderMiddleware(svc))
	r.GET("/test", func(c *gin.Context) {
		val, ok := c.Get("orderService")
		if !ok {
			c.Status(http.StatusInternalServerError)
			return
		}
		captured, ok = val.(*OrderService)
		if !ok {
			c.Status(http.StatusInternalServerError)
			return
		}
		c.Status(http.StatusOK)
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	if captured != svc {
		t.Error("middleware did not inject the correct OrderService")
	}
}

// TestGetOrder tests the getOrder handler.
func TestGetOrder(t *testing.T) {
	tests := []struct {
		name       string
		orderID    string
		repo       *mockOrderRepo
		wantStatus int
	}{
		{
			name:    "valid order",
			orderID: "42",
			repo: &mockOrderRepo{
				orders: map[string]Order{
					"42": {OrderID: "42", CustomerID: "cust1", Status: Pending},
				},
			},
			wantStatus: http.StatusOK,
		},
		{
			name:       "invalid order id (non-numeric)",
			orderID:    "abc",
			repo:       &mockOrderRepo{},
			wantStatus: http.StatusBadRequest,
		},
		{
			name:    "order not found",
			orderID: "99",
			repo: &mockOrderRepo{
				getErr: errors.New("not found"),
			},
			wantStatus: http.StatusInternalServerError,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			svc := NewOrderService(tc.repo)
			r := setupRouter(svc)

			req := httptest.NewRequest(http.MethodGet, "/order/"+tc.orderID, nil)
			w := httptest.NewRecorder()
			r.ServeHTTP(w, req)

			if w.Code != tc.wantStatus {
				t.Errorf("expected status %d, got %d", tc.wantStatus, w.Code)
			}
		})
	}
}

// TestUpdateOrder tests the updateOrder handler.
func TestUpdateOrder(t *testing.T) {
	tests := []struct {
		name       string
		body       interface{}
		repo       *mockOrderRepo
		wantStatus int
	}{
		{
			name: "valid update",
			body: Order{
				OrderID:    "1",
				CustomerID: "cust1",
				Status:     Processing,
				Items:      []Item{{Product: 1, Quantity: 2, Price: 9.99}},
			},
			repo:       &mockOrderRepo{},
			wantStatus: http.StatusOK,
		},
		{
			name: "invalid order id (non-numeric)",
			body: Order{
				OrderID:    "notanumber",
				CustomerID: "cust1",
				Status:     Processing,
			},
			repo:       &mockOrderRepo{},
			wantStatus: http.StatusBadRequest,
		},
		{
			name: "database error on update",
			body: Order{
				OrderID:    "5",
				CustomerID: "cust2",
				Status:     Complete,
			},
			repo:       &mockOrderRepo{updateErr: errors.New("db error")},
			wantStatus: http.StatusInternalServerError,
		},
		{
			name:       "malformed JSON body",
			body:       "not-json",
			repo:       &mockOrderRepo{},
			wantStatus: http.StatusBadRequest,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			svc := NewOrderService(tc.repo)
			r := setupRouter(svc)

			var bodyBytes []byte
			var err error
			if s, ok := tc.body.(string); ok {
				bodyBytes = []byte(s)
			} else {
				bodyBytes, err = json.Marshal(tc.body)
				if err != nil {
					t.Fatalf("failed to marshal body: %v", err)
				}
			}

			req := httptest.NewRequest(http.MethodPut, "/order", bytes.NewReader(bodyBytes))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()
			r.ServeHTTP(w, req)

			if w.Code != tc.wantStatus {
				t.Errorf("expected status %d, got %d", tc.wantStatus, w.Code)
			}
		})
	}
}

// TestUnmarshalOrderFromQueue tests the unmarshalOrderFromQueue helper.
func TestUnmarshalOrderFromQueue(t *testing.T) {
	tests := []struct {
		name      string
		input     string
		wantItems int
		wantErr   bool
	}{
		{
			name: "valid order with items",
			input: `{
				"customerId": "customer-1",
				"items": [
					{"productId": 1, "quantity": 2, "price": 5.99},
					{"productId": 2, "quantity": 1, "price": 12.50}
				]
			}`,
			wantItems: 2,
			wantErr:   false,
		},
		{
			name: "valid order with no items",
			input: `{
				"customerId": "customer-2",
				"items": []
			}`,
			wantItems: 0,
			wantErr:   false,
		},
		{
			name:    "invalid JSON",
			input:   `{not valid json`,
			wantErr: true,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			order, err := unmarshalOrderFromQueue([]byte(tc.input))
			if tc.wantErr {
				if err == nil {
					t.Error("expected error but got nil")
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if len(order.Items) != tc.wantItems {
				t.Errorf("expected %d items, got %d", tc.wantItems, len(order.Items))
			}
			if order.Status != Pending {
				t.Errorf("expected status Pending (%d), got %d", Pending, order.Status)
			}
			// OrderID should be set to a non-empty string
			if order.OrderID == "" {
				t.Error("expected OrderID to be set after unmarshaling")
			}
		})
	}
}
