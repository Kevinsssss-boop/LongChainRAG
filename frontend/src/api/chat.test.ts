import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { chatStream } from './chat';

/** 造一个假的 SSE 响应体。 */
function sseResponse(events: string[]) {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      for (const e of events) controller.enqueue(encoder.encode(e));
      controller.close();
    },
  });
  return { ok: true, body };
}

function run(events: string[]) {
  const onToken = vi.fn();
  const onCitations = vi.fn();
  const onDone = vi.fn();
  const onError = vi.fn();

  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse(events)));
  chatStream('s1', 'q', onToken, onCitations, onDone, onError);

  return { onToken, onCitations, onDone, onError };
}

describe('chatStream 的收尾行为', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'test-token');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('收到 done 事件时调用 onDone', async () => {
    const { onDone } = run([
      'data: {"type":"token","content":"hi"}\n\n',
      'data: {"type":"done"}\n\n',
    ]);

    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());
    // 只调一次 —— 兜底逻辑不能在已经收到 done 之后再补一次
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('服务端没发 done 就断开时，兜底调用 onDone', async () => {
    // 这是「输入框永久禁用」那个 bug 的回归测试。
    // 服务端中途断开、或反向代理截断响应时，reader 会正常读到 EOF，
    // 循环干净退出，但 onDone / onError 一个都没被调用过 ——
    // 调用方的 streaming 就永远停在 true，只能刷新页面。
    const { onDone } = run(['data: {"type":"token","content":"hi"}\n\n']);

    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());
  });

  it('收到 error 事件后不再补一次 onDone', async () => {
    const { onDone, onError } = run(['data: {"type":"error","content":"boom"}\n\n']);

    await vi.waitFor(() => expect(onError).toHaveBeenCalledWith('boom'));
    expect(onDone).not.toHaveBeenCalled();
  });

  it('把 token 和 citations 交给对应的回调', async () => {
    const { onToken, onCitations } = run([
      'data: {"type":"token","content":"你好"}\n\n',
      'data: {"type":"citations","data":[{"source":"a.pdf"}]}\n\n',
      'data: {"type":"done"}\n\n',
    ]);

    await vi.waitFor(() => expect(onToken).toHaveBeenCalledWith('你好'));
    expect(onCitations).toHaveBeenCalledWith([{ source: 'a.pdf' }]);
  });

  it('HTTP 非 2xx 时把 detail 交给 onError', async () => {
    const onError = vi.fn();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: '会话不存在' }),
      })
    );

    chatStream('s1', 'q', vi.fn(), vi.fn(), vi.fn(), onError);

    await vi.waitFor(() => expect(onError).toHaveBeenCalledWith('会话不存在'));
  });

  it('响应体为空时不抛异常', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, body: null }));
    const onError = vi.fn();

    chatStream('s1', 'q', vi.fn(), vi.fn(), vi.fn(), onError);

    // 给微任务一个机会跑完
    await new Promise((r) => setTimeout(r, 0));
    expect(onError).not.toHaveBeenCalled();
  });
});
