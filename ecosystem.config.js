module.exports = {
  apps: [{
    name: 'x-commit',
    script: 'uv',
    args: 'run x-commit serve',
    cwd: './',
    interpreter: 'none',
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    time: true
  }]
};