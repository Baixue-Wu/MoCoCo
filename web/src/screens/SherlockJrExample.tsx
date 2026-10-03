import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'

const root = 'https://baixue-wu.github.io/MoCoCo'
const release = 'https://github.com/Baixue-Wu/MoCoCo/releases/download/demo-sherlock-jr-v1'

const script = [
  '别人看电影，他直接钻进银幕！可这位梦里无所不能的神探，现实中却刚被当成小偷赶出门。基顿这场翻身仗，还得从一块失踪的怀表说起。',
  '放映员一边在影院扫地，一边捧着侦探入门书，盼着自己也能破大案。恋爱经费有限，他买盒便宜巧克力，还悄悄改高价签，去见心上人。偏偏情敌也来了，礼物更贵，手段更黑。',
  '情敌偷走女孩父亲的怀表，拿去典当，再把当票塞进放映员口袋。怀表一丢，放映员立刻照着书展开调查，结果搜来搜去，证据竟在自己身上！侦探没当成，倒成了头号嫌犯。',
  '被赶出去的放映员不甘心，紧跟情敌，想找出真相。谁知一路跟到火车旁，反把自己折腾得狼狈不堪。他垂头丧气回到放映室，睡着了，女孩却没有放弃，拿着当票继续查。',
  '睡梦中，放映员的身影离开身体，走进银幕。刚站稳，花园变街道，街道变悬崖，转眼又成海面！他的位置没动，布景却不停换，刚想坐下，屁股底下已经空了。连电影剪辑都能把人耍得团团转。',
  '终于，梦里的他化身福尔摩斯二世，调查珍珠失窃案。现实中的熟面孔，也变成了银幕里的角色。坏人布下毒酒、机关和会爆炸的台球，等他中招。他却悠然挥杆，危险球始终没撞上，急得坏人比他还紧张。',
  '女孩落入险境，神探立刻追去营救。逃跑时，他穿窗瞬间换装，还借助手掩护突然消失。接着坐上摩托车车把，司机掉了，他竟浑然不知！一路穿过车流、险越断桥，终于赶到女孩身边，驾车逃走，却又冲进湖里。',
  '正当梦里的英雄忙着脱险，放映员醒了。女孩已经查明典当怀表的是情敌，亲自来替他洗清冤屈。他看看银幕上的情侣，现学现用，牵手、拥抱、亲吻。可银幕一转，夫妻已经抱上孩子，他当场挠头：这下一步，电影是不是教得太快了？',
]

const stages = [
  ['01', '预处理', '将原片切分为镜头，抽取关键帧，为代表性画面写说明。'],
  ['02', '文案', '按现实—梦境—现实的叙事结构写成 8 段中文解说，再提取每段的画面意图。'],
  ['03', '镜头', '按语义检索候选镜头，人工复核梦境转场、台球和摩托追逐等关键画面。'],
  ['04', '剪辑', '安排镜头顺序与时长，让画面跟随旁白节奏。'],
  ['05', '配音', '生成中文旁白，并将每一段的时间对齐。'],
  ['06', '导出', '合成 2 分 45 秒视频，烧录中文字幕。'],
]

export function SherlockJrExample() {
  const { t } = useI18n()

  return (
    <div className="example-page">
      <Link to="/" className="small">← {t('common.back')}</Link>
      <div className="example-heading">
        <div>
          <span className="badge badge-accent">{t('example.badge')}</span>
          <h1>{t('example.title')}</h1>
          <p className="muted">{t('example.intro')}</p>
        </div>
        <Link className="btn btn-primary" to="/">{t('example.try')}</Link>
      </div>

      <div className="card example-video">
        <video controls preload="metadata" poster={`${root}/assets/sherlock-jr-poster.jpg`} src={`${root}/assets/sherlock-jr-recap.mp4`} />
        <div className="example-video-links">
          <a href={`${release}/sherlock-jr-recap-full.mp4`}>{t('example.download_result')}</a>
          <a href={`${release}/Sherlock_Jr.1924.webm`}>{t('example.download_source')}</a>
        </div>
      </div>

      <section className="example-section">
        <h2>{t('example.workflow')}</h2>
        <div className="example-stage-grid">
          {stages.map(([number, title, description]) => (
            <div key={number} className="card example-stage">
              <span className="small muted">{number}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="example-section">
        <h2>{t('example.script')}</h2>
        <p className="muted">{t('example.script_hint')}</p>
        <div className="card example-script">
          {script.map((paragraph, index) => (
            <div key={index} className="example-script-paragraph">
              <span className="badge">{String(index + 1).padStart(2, '0')}</span>
              <p>{paragraph}</p>
            </div>
          ))}
        </div>
      </section>

      <p className="small muted example-source">
        {t('example.source_note')}{' '}
        <a href="https://commons.wikimedia.org/wiki/File:Sherlock_Jr.(1924).webm" target="_blank" rel="noreferrer">Wikimedia Commons</a>
      </p>
    </div>
  )
}
