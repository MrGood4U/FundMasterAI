from unittest.mock import MagicMock, patch

from alert_checker import AlertChecker


def _make_alert(**overrides):
    return dict({
        "id": 1, "asset_type": "stock", "asset_code": "000001",
        "alert_type": "price_above", "trigger_mode": "price",
        "trigger_price": 15.00, "trigger_pct": None,
        "reference_trans_id": None,
        "notify_phone": 0, "notify_email": 0,
    }, **overrides)


class TestGetCostBasis:
    def test_with_reference_transaction(self):
        checker = AlertChecker()
        checker.trans_dao = MagicMock()
        checker.trans_dao.get_by_id.return_value = {"id": 10, "price": 12.00}

        alert = _make_alert(reference_trans_id=10)
        cost = checker._get_cost_basis(alert)

        assert cost == 12.00
        checker.trans_dao.get_by_id.assert_called_once_with(10)

    def test_reference_transaction_not_found(self):
        checker = AlertChecker()
        checker.trans_dao = MagicMock()
        checker.trans_dao.get_by_id.return_value = None

        alert = _make_alert(reference_trans_id=999)
        cost = checker._get_cost_basis(alert)

        assert cost is None

    def test_weighted_average_no_reference(self):
        checker = AlertChecker()
        checker.trans_dao = MagicMock()
        checker.trans_dao.list_by_user.return_value = [
            {"trans_type": "buy", "quantity": 100, "price": 10.00, "fee": 5.0},
            {"trans_type": "buy", "quantity": 200, "price": 11.00, "fee": 10.0},
            {"trans_type": "sell", "quantity": 50, "price": 12.00, "fee": 3.0},
        ]

        alert = _make_alert(asset_type="stock", asset_code="000001")
        cost = checker._get_cost_basis(alert)

        # total_cost = 100*10 + 5 + 200*11 + 10 = 1005 + 2210 = 3215
        # total_qty = 100 + 200 = 300 (sell doesn't affect cost basis)
        # avg = 3215 / 300 ≈ 10.7167
        expected = (100 * 10.0 + 5.0 + 200 * 11.0 + 10.0) / 300.0
        assert round(cost, 4) == round(expected, 4)
        checker.trans_dao.list_by_user.assert_called_once_with(
            asset_type="stock", asset_code="000001",
        )

    def test_weighted_average_no_buys(self):
        checker = AlertChecker()
        checker.trans_dao = MagicMock()
        checker.trans_dao.list_by_user.return_value = [
            {"trans_type": "sell", "quantity": 100, "price": 10.00, "fee": 5.0},
        ]

        alert = _make_alert(asset_type="stock", asset_code="000001")
        cost = checker._get_cost_basis(alert)

        assert cost is None


class TestIsTriggeredPriceMode:
    def test_price_above_triggered(self):
        checker = AlertChecker()
        alert = _make_alert(trigger_mode="price", alert_type="price_above",
                            trigger_price=15.00)
        assert checker._is_triggered(alert, 15.00) is True
        assert checker._is_triggered(alert, 15.01) is True
        assert checker._is_triggered(alert, 14.99) is False

    def test_price_below_triggered(self):
        checker = AlertChecker()
        alert = _make_alert(trigger_mode="price", alert_type="price_below",
                            trigger_price=15.00)
        assert checker._is_triggered(alert, 15.00) is True
        assert checker._is_triggered(alert, 14.99) is True
        assert checker._is_triggered(alert, 15.01) is False

    def test_stop_profit_triggered(self):
        checker = AlertChecker()
        alert = _make_alert(trigger_mode="price", alert_type="stop_profit",
                            trigger_price=20.00)
        assert checker._is_triggered(alert, 20.00) is True
        assert checker._is_triggered(alert, 21.00) is True
        assert checker._is_triggered(alert, 19.99) is False

    def test_stop_loss_triggered(self):
        checker = AlertChecker()
        alert = _make_alert(trigger_mode="price", alert_type="stop_loss",
                            trigger_price=8.00)
        assert checker._is_triggered(alert, 8.00) is True
        assert checker._is_triggered(alert, 7.50) is True
        assert checker._is_triggered(alert, 8.01) is False


class TestIsTriggeredPctMode:
    def test_price_above_pct_triggered(self):
        checker = AlertChecker()
        checker._get_cost_basis = MagicMock(return_value=10.00)

        alert = _make_alert(trigger_mode="pct", alert_type="price_above",
                            trigger_pct=0.15)
        # cost=10, price=11.50 → change=0.15 → triggered (>= 0.15)
        assert checker._is_triggered(alert, 11.50) is True
        # cost=10, price=11.49 → change=0.149 → NOT triggered
        assert checker._is_triggered(alert, 11.49) is False

    def test_price_below_pct_triggered(self):
        checker = AlertChecker()
        checker._get_cost_basis = MagicMock(return_value=10.00)

        alert = _make_alert(trigger_mode="pct", alert_type="price_below",
                            trigger_pct=-0.10)
        # cost=10, price=9.00 → change=-0.10 → triggered (<= -0.10)
        assert checker._is_triggered(alert, 9.00) is True
        # cost=10, price=9.01 → change=-0.099 → NOT triggered
        assert checker._is_triggered(alert, 9.01) is False

    def test_stop_profit_pct_triggered(self):
        checker = AlertChecker()
        checker._get_cost_basis = MagicMock(return_value=10.00)

        alert = _make_alert(trigger_mode="pct", alert_type="stop_profit",
                            trigger_pct=0.20)
        assert checker._is_triggered(alert, 12.00) is True   # +20%
        assert checker._is_triggered(alert, 11.99) is False  # +19.9%

    def test_stop_loss_pct_triggered(self):
        checker = AlertChecker()
        checker._get_cost_basis = MagicMock(return_value=10.00)

        alert = _make_alert(trigger_mode="pct", alert_type="stop_loss",
                            trigger_pct=-0.08)
        assert checker._is_triggered(alert, 9.20) is True    # -8%
        assert checker._is_triggered(alert, 9.21) is False   # -7.9%

    def test_no_cost_basis_returns_false(self):
        checker = AlertChecker()
        checker._get_cost_basis = MagicMock(return_value=None)

        alert = _make_alert(trigger_mode="pct", alert_type="price_above",
                            trigger_pct=0.15)
        assert checker._is_triggered(alert, 15.00) is False


class TestCheckAndNotify:
    def test_no_enabled_alerts(self):
        checker = AlertChecker()
        checker.alert_dao = MagicMock()
        checker.alert_dao.list_by_user.return_value = []

        checker.check_and_notify()
        # Should complete without error

    def test_price_unavailable_skipped(self):
        checker = AlertChecker()
        checker.alert_dao = MagicMock()
        checker.alert_dao.list_by_user.return_value = [
            _make_alert(id=1),
        ]
        checker.market = MagicMock()
        checker.market.get_realtime_price.return_value = None

        checker.check_and_notify()
        # Alert skipped, no update calls
        checker.alert_dao.update.assert_not_called()
        checker.alert_dao.mark_notified.assert_not_called()

    def test_alert_not_triggered(self):
        checker = AlertChecker()
        checker.alert_dao = MagicMock()
        checker.alert_dao.list_by_user.return_value = [
            _make_alert(id=1),
        ]
        checker.market = MagicMock()
        checker.market.get_realtime_price.return_value = {"current_price": 10.00}
        checker._is_triggered = MagicMock(return_value=False)

        checker.check_and_notify()
        checker.alert_dao.update.assert_not_called()

    def test_alert_triggered_no_notify_channels(self):
        checker = AlertChecker()
        checker.alert_dao = MagicMock()
        checker.alert_dao.list_by_user.return_value = [
            _make_alert(id=1, notify_phone=0, notify_email=0),
        ]
        checker.market = MagicMock()
        checker.market.get_realtime_price.return_value = {"current_price": 16.00}
        checker.profile_dao = MagicMock()
        checker.profile_dao.get.return_value = None

        checker.check_and_notify()

        checker.alert_dao.update.assert_called_once_with(1, is_enabled=0)
        checker.alert_dao.mark_notified.assert_called_once_with(1)

    def test_alert_triggered_with_phone_notify(self):
        checker = AlertChecker()
        checker.alert_dao = MagicMock()
        checker.alert_dao.list_by_user.return_value = [
            _make_alert(id=1, notify_phone=1, notify_email=0),
        ]
        checker.market = MagicMock()
        checker.market.get_realtime_price.return_value = {"current_price": 16.00}
        checker.profile_dao = MagicMock()
        checker.profile_dao.get.return_value = {"phone": "13800000000", "email": None}

        with patch("alert_checker.send_phone_alert") as mock_phone, \
             patch("alert_checker.send_email_alert") as mock_email:
            checker.check_and_notify()

        mock_phone.assert_called_once()
        mock_email.assert_not_called()
        checker.alert_dao.update.assert_called_once_with(1, is_enabled=0)

    def test_alert_triggered_with_email_notify(self):
        checker = AlertChecker()
        checker.alert_dao = MagicMock()
        checker.alert_dao.list_by_user.return_value = [
            _make_alert(id=1, notify_phone=0, notify_email=1),
        ]
        checker.market = MagicMock()
        checker.market.get_realtime_price.return_value = {"current_price": 16.00}
        checker.profile_dao = MagicMock()
        checker.profile_dao.get.return_value = {"phone": None, "email": "user@test.com"}

        with patch("alert_checker.send_phone_alert") as mock_phone, \
             patch("alert_checker.send_email_alert") as mock_email:
            checker.check_and_notify()

        mock_phone.assert_not_called()
        mock_email.assert_called_once()
        checker.alert_dao.update.assert_called_once_with(1, is_enabled=0)

    def test_alert_triggered_with_both_channels(self):
        checker = AlertChecker()
        checker.alert_dao = MagicMock()
        checker.alert_dao.list_by_user.return_value = [
            _make_alert(id=1, notify_phone=1, notify_email=1),
        ]
        checker.market = MagicMock()
        checker.market.get_realtime_price.return_value = {"current_price": 16.00}
        checker.profile_dao = MagicMock()
        checker.profile_dao.get.return_value = {
            "phone": "13800000000", "email": "user@test.com",
        }

        with patch("alert_checker.send_phone_alert") as mock_phone, \
             patch("alert_checker.send_email_alert") as mock_email:
            checker.check_and_notify()

        mock_phone.assert_called_once()
        mock_email.assert_called_once()

    def test_alert_triggered_no_profile_skips_notify(self):
        checker = AlertChecker()
        checker.alert_dao = MagicMock()
        checker.alert_dao.list_by_user.return_value = [
            _make_alert(id=1, notify_phone=1, notify_email=1),
        ]
        checker.market = MagicMock()
        checker.market.get_realtime_price.return_value = {"current_price": 16.00}
        checker.profile_dao = MagicMock()
        checker.profile_dao.get.return_value = None

        with patch("alert_checker.send_phone_alert") as mock_phone, \
             patch("alert_checker.send_email_alert") as mock_email:
            checker.check_and_notify()

        mock_phone.assert_not_called()
        mock_email.assert_not_called()
        # Still disables the alert even without notifications
        checker.alert_dao.update.assert_called_once_with(1, is_enabled=0)

    def test_multiple_alerts_mixed(self):
        checker = AlertChecker()
        checker.alert_dao = MagicMock()
        checker.alert_dao.list_by_user.return_value = [
            _make_alert(id=1),   # triggered
            _make_alert(id=2),   # not triggered
            _make_alert(id=3),   # triggered
        ]

        # price_info for alert 1: triggers
        # price_info for alert 2: does not trigger
        # price_info for alert 3: triggers
        def fake_price(a_type, a_code):
            return {"current_price": 16.00}

        def fake_triggered(alert, price):
            return alert["id"] in (1, 3)

        checker.market = MagicMock()
        checker.market.get_realtime_price.side_effect = fake_price
        checker._is_triggered = fake_triggered
        checker.profile_dao = MagicMock()
        checker.profile_dao.get.return_value = None

        checker.check_and_notify()

        assert checker.alert_dao.update.call_count == 2
        checker.alert_dao.update.assert_any_call(1, is_enabled=0)
        checker.alert_dao.update.assert_any_call(3, is_enabled=0)

    def test_checker_handles_per_alert_exception(self):
        checker = AlertChecker()
        checker.alert_dao = MagicMock()
        checker.alert_dao.list_by_user.return_value = [
            _make_alert(id=1),   # will raise during processing
            _make_alert(id=2),   # should still be processed
        ]

        call_count = 0

        def fake_price(a_type, a_code):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("market error")
            return {"current_price": 16.00}

        checker.market = MagicMock()
        checker.market.get_realtime_price.side_effect = fake_price
        checker.profile_dao = MagicMock()
        checker.profile_dao.get.return_value = None

        # Should not raise — per-alert errors are caught
        checker.check_and_notify()

        # Alert 2 was still processed
        checker.alert_dao.update.assert_called_once_with(2, is_enabled=0)
