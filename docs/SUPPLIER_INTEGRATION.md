# Supplier Network integration

The safe default is `NullSupplierNetworkClient`. The HTTP implementation targets authorized summary, product, offer, and capability endpoints by HS/product identity. Market must never read the Supplier database directly.

A future supply response may contain supplier count, product count, active offers, pricing, MOQ, stock, and lead time. Those fields feed a separate Supply Fit model. Only after supply, economics, competition, and entry-risk evidence exists may the product introduce a Distribution Opportunity score.

Market Attractiveness remains a demand-side score and must not be renamed or represented as projected sales.

The contract supports supplier/product/offer counts, price distribution, currency, MOQ, stock, lead time, certification, dropship capability, and nullable historical delivery/quality measures. Confirmed Supplier data carries reliability A and remains independently traceable. Supplier failures leave Supply Fit null rather than lowering it to zero.
