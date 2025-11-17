# Fetch web
## frequency
modify .github/workflows/monitor.yml ：

once a week: '0 1 * * 1' (Monday)
every month: '0 1 1 * *' (1st every month)
everyday: '0 1 * * *'

# Test
python monitor.py
