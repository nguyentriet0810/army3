# Army3 Offline

Muc tieu cua du an la xay dung mot phien ban Army3 chay hoan toan offline

## Tai lieu dau vao

Thu muc `Mobiarmy3HA_3.0.0_GOC/` chua client Unity IL2CPP goc dung cho viec
phan tich tuong thich. Thu muc nay duoc giu nguyen tai may cuc bo va khong duoc
dua vao lich su Git.

## Nguyen tac

- Khong sua truc tiep client goc.
- Cac cong cu, ma nguon server offline va tai lieu phan tich se duoc quan ly
  trong repository nay.
- Dau ra tu dong, tep dump va ban build khong duoc commit.

## Kiem thu protocol Python

Codec cho duong ket noi va dang nhap cuc bo nam trong
`server/army3_protocol/` va chi dung thu vien chuan Python:

```powershell
python -m unittest discover -s tests -v
```

Codec M4 khong tu mo socket; server M5 import codec nay va chi bind mac dinh
tren `127.0.0.1`.

## Chay local server

Server M5 chi dung thu vien chuan Python va tu choi bind vao dia chi khong
phai loopback:

```powershell
python -m server
```

Endpoint mac dinh la `127.0.0.1:19150`. Xem `docs/local-server.md` de biet
state machine, tuy chon khoi dong va cac gioi han chua duoc kiem chung runtime.

Cong cu M6 tao ban sao client da patch trong `build/`:

```powershell
python -m tools.redirect_client verify-source
python -m tools.redirect_client create
python -m tools.redirect_client verify-copy
```

Xem `docs/client-redirection.md`. Khong chay client goc hoac ban sao neu chua
co phep va chua bat co che chan outbound.
